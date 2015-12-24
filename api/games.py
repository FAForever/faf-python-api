import distutils.util
from faf.api.game_stats_schema import GameStatsSchema, GamePlayerStatsSchema
from faf.game_validity import GameValidity
from faf.victory_condition import VictoryCondition
from flask import request
from api import app, InvalidUsage
from api.query_commons import fetch_data

MAX_GAME_PAGE_SIZE = 1000
MAX_PLAYER_PAGE_SIZE = MAX_GAME_PAGE_SIZE * 12

GAME_SELECT_EXPRESSIONS = {
    'id': 'gs.id',
    'game_name': 'gameName',
    'map_name': 'tm.name',
    'victory_condition': 'gameType',
    'game_mod': 'gameMod',
    'host': 'host',
    'start_time': 'startTime',
    'validity': 'validity'
}

PLAYER_SELECT_EXPRESSIONS = {
    'id': 'gps.id',
    'game_id': 'gameId',
    'player_id': 'playerId',
    'login': 'l.login',
    'team': 'team',
    'faction': 'faction',
    'color': 'color',
    'has_ai': 'AI',
    'place': 'place',
    'mean': 'r.mean',
    'deviation': 'r.deviation',
    'score': 'score',
    'score_time': 'scoreTime'
}

GAME_STATS_TABLE = 'game_stats gs'
GAME_PLAYER_STATS_TABLE = 'game_player_stats gps'
LOGIN_TABLE = 'login'

MAP_JOIN = ' INNER JOIN table_map tm ON tm.id = gs.mapId'
LOGIN_JOIN = ' INNER JOIN login l ON l.id = gps.playerId'
GLOBAL_JOIN = ' INNER JOIN global_rating r ON r.id = gps.playerId'
LADDER1V1_JOIN = ' INNER JOIN ladder1v1_rating r ON r.id = gps.playerId'

GAME_STATS_HEADER_EXPRESSION = 'game_stats gs' + MAP_JOIN + ' WHERE gs.id'
GAME_PLAYER_STATS_HEADER_EXPRESSION = 'game_player_stats gps' + LOGIN_JOIN + ' {} WHERE gameId '
SUB_HEADER_EXPRESSION_HEAD = ' IN (SELECT playerCount.gameId FROM (' \
                        'SELECT gps.gameId, COUNT(playerId) AS `playerCount` FROM game_player_stats gps INNER JOIN (' \
                        'SELECT gameId FROM game_player_stats gps INNER JOIN game_stats gs ON gs.id = gps.gameId'
SUB_HEADER_EXPRESSION_FOOT = ') games ON gps.gameId = games.gameId GROUP BY gps.gameId) playerCount '
COUNT_TABLE_EXPRESSION_HEADER = 'INNER JOIN (SELECT gameId, COUNT(playerId) AS `playerCount` FROM game_player_stats gps'
COUNT_TABLE_EXPRESSION_FOOTER = 'GROUP BY gameId) maxPlayerRatingCount ON ' \
                                'playerCount.playerCount = maxPlayerRatingCount.playerCount ' \
                                'AND playerCount.gameId = maxPlayerRatingCount.gameId'
FOOTER_EXPRESSION = ')'

MAX_RATING_WHERE_EXPRESSION = '%s >= ROUND(r.mean - 3 * r.deviation)'
MIN_RATING_WHERE_EXPRESSION = '%s <= ROUND(r.mean - 3 * r.deviation)'
MAP_NAME_WHERE_EXPRESSION = '{} tm.name = %s'
MAX_PLAYER_WHERE_EXPRESSION = 'playerCount.playerCount <= %s'
MIN_PLAYER_WHERE_EXPRESSION = 'playerCount.playerCount >= %s'
VICTORY_CONDITION_WHERE_EXPRESSION = 'gs.gameType = %s'
GROUP_BY_EXPRESSION = ' GROUP BY gameId HAVING COUNT(*) > {} '

AND = ' AND '
WHERE = ' WHERE '
NOT = 'NOT'


@app.route('/games')
def games():
    player_list = request.args.get('filter[players]')
    map_name = request.args.get('filter[map_name]')
    map_exclude = request.args.get('filter[map_exclude]')
    max_rating = request.args.get('filter[max_rating]')
    min_rating = request.args.get('filter[min_rating]')
    victory_condition = request.args.get('filter[victory_condition]')
    rating_type = request.args.get('filter[rating_type]')
    max_players = request.args.get('filter[max_player_count]')
    min_players = request.args.get('filter[min_player_count]')

    if rating_type and not (max_rating or min_rating):
        return {'errors': [{'title': 'Missing max/min_rating parameters'}]}, 422

    if map_exclude and not map_name:
        return {'errors': [{'title': 'Missing map_name parameter'}]}, 422

    if player_list or map_name or max_rating or min_rating or victory_condition:
        if not map_exclude:
            map_exclude = 'False'

        select_expression, args = build_query(victory_condition, map_name, map_exclude, max_rating, min_rating,
                                              player_list,
                                              rating_type, max_players, min_players)

        game_stats_select_expression = GAME_STATS_HEADER_EXPRESSION + select_expression + FOOTER_EXPRESSION
        game_player_stats_select_expression = build_game_player_stats_query(select_expression,
                                                                            rating_type) + FOOTER_EXPRESSION
        game_results = fetch_data(GameStatsSchema(), game_stats_select_expression, GAME_SELECT_EXPRESSIONS,
                                  MAX_GAME_PAGE_SIZE, request,
                                  args=args, enricher=enricher, sort='-id')
        player_results = fetch_data(GamePlayerStatsSchema(), game_player_stats_select_expression,
                                    PLAYER_SELECT_EXPRESSIONS, MAX_PLAYER_PAGE_SIZE, request, args=args,
                                    sort='-game_id')
    else:
        game_results = fetch_data(GameStatsSchema(), GAME_STATS_TABLE, GAME_SELECT_EXPRESSIONS, MAX_GAME_PAGE_SIZE,
                                  request,
                                  enricher=enricher, sort='-id')
        player_results = fetch_data(GamePlayerStatsSchema(), GAME_PLAYER_STATS_TABLE + GLOBAL_JOIN + LOGIN_JOIN,
                                    PLAYER_SELECT_EXPRESSIONS, MAX_PLAYER_PAGE_SIZE, request, sort='-game_id')
    return join_game_and_player_results(game_results, player_results)


@app.route('/games/<game_id>')
def game(game_id):
    game_result = fetch_data(GameStatsSchema(), GAME_STATS_TABLE, GAME_SELECT_EXPRESSIONS, MAX_GAME_PAGE_SIZE, request,
                             where='id = %s', args=game_id, many=False, enricher=enricher)

    if 'id' not in game_result['data']:
        return {'errors': [{'title': 'No game with this game ID was found'}]}, 404

    player_select_expression = GAME_PLAYER_STATS_TABLE + GLOBAL_JOIN + LOGIN_JOIN
    player_results = fetch_data(GamePlayerStatsSchema(), player_select_expression, PLAYER_SELECT_EXPRESSIONS,
                                MAX_GAME_PAGE_SIZE,
                                request, where='gameId = %s', args=game_id)

    game_result['data']['relationships'] = dict(players=player_results)

    return game_result


def enricher(game):
    if 'victory_condition' in game:
        if not game['victory_condition']:
            del game['victory_condition']
        else:
            game['victory_condition'] = VictoryCondition(int(game['victory_condition'])).name

    if 'validity' in game:
        if not game['validity']:
            del game['validity']
        else:
            game['validity'] = GameValidity(int(game['validity'])).name


def build_query(victory_condition, map_name, map_exclude, max_rating, min_rating, player_list, rating_type, max_players,
                min_players):
    table_expression = SUB_HEADER_EXPRESSION_HEAD
    where_expression = ''
    args = list()
    first = True
    players = None

    if player_list:
        table_expression += LOGIN_JOIN
        players = player_list.split(',')
        player_expression = LOGIN_TABLE + ' IN ({})'.format(','.join(['%s'] * len(players)))
        args += players
        first, where_expression = append_where_expression(first, where_expression, player_expression)

    if map_name:
        table_expression += MAP_JOIN
        args.append(map_name)
        try:
            map_exclude = distutils.util.strtobool(map_exclude)
        except ValueError:
            throw_malformed_query_error('map_name')
        if map_exclude:
            first, where_expression = append_where_expression(first, where_expression,
                                                              MAP_NAME_WHERE_EXPRESSION.format(NOT))
        else:
            first, where_expression = append_where_expression(first, where_expression,
                                                              MAP_NAME_WHERE_EXPRESSION.format(''))

    if victory_condition:
        condition = VictoryCondition.from_gpgnet_string(victory_condition)
        # Returns false regardless if enum is assigned when "if condition"
        if condition is not None:
            args.append(str(condition.value))
            first, where_expression = append_where_expression(first, where_expression, VICTORY_CONDITION_WHERE_EXPRESSION)
        else:
            throw_malformed_query_error('victory_condition')

    if players:
        where_expression += GROUP_BY_EXPRESSION.format(len(players) - 1)
    else:
        where_expression += GROUP_BY_EXPRESSION.format(0)

    table_expression += where_expression + SUB_HEADER_EXPRESSION_FOOT

    if max_rating or min_rating:
        first_rating = True
        table_expression += COUNT_TABLE_EXPRESSION_HEADER
        if max_rating:
            table_expression, where_expression, args, first_rating = build_rating_expression(max_rating, first_rating,
                                                                                             rating_type,
                                                                                             table_expression,
                                                                                             MAX_RATING_WHERE_EXPRESSION,
                                                                                             args)
            table_expression += where_expression
        if min_rating:
            table_expression, where_expression, args, first_rating = build_rating_expression(min_rating, first_rating,
                                                                                             rating_type,
                                                                                             table_expression,
                                                                                             MIN_RATING_WHERE_EXPRESSION,
                                                                                             args)
            table_expression += where_expression
        table_expression += COUNT_TABLE_EXPRESSION_FOOTER

    first_count = True
    if max_players:
        table_expression, args, first_count = build_player_count_expression(max_players, first_count, table_expression,
                                                                            MAX_PLAYER_WHERE_EXPRESSION, args)

    if min_players:
        table_expression, args, first_count = build_player_count_expression(min_players, first_count, table_expression,
                                                                            MIN_PLAYER_WHERE_EXPRESSION, args)

    return table_expression, args


def build_rating_expression(rating, first, rating_type, table_expression,
                            rating_where_expression, args):
    try:
        rating = int(rating)
    except ValueError:
        throw_malformed_query_error('rating field')

    if rating_type == 'ladder':
        if LADDER1V1_JOIN not in table_expression:
            table_expression += LADDER1V1_JOIN
    else:
        if GLOBAL_JOIN not in table_expression:
            table_expression += GLOBAL_JOIN

    args.append(rating)
    first, where_expression = append_where_expression(first, '', rating_where_expression)
    return table_expression, where_expression, args, first


def build_player_count_expression(player_count, first, table_expression, player_count_where_expression, args):
    try:
        player_count = int(player_count)
    except ValueError:
        throw_malformed_query_error('player count field')

    args.append(player_count)
    first, table_expression = append_where_expression(first, table_expression, player_count_where_expression)
    return table_expression, args, first


def append_where_expression(first, where_expression, format_expression):
    if first:
        where_expression += WHERE + format_expression
        first = False
    else:
        where_expression += AND + format_expression
    return first, where_expression


def build_game_player_stats_query(select_expression, rating_type):
    if rating_type == 'ladder':
        table_expression = GAME_PLAYER_STATS_HEADER_EXPRESSION.format(LADDER1V1_JOIN, LOGIN_JOIN)
    else:
        table_expression = GAME_PLAYER_STATS_HEADER_EXPRESSION.format(GLOBAL_JOIN, LOGIN_JOIN)
    return table_expression + select_expression


def join_game_and_player_results(game_results, player_results):
    game_player = dict()
    for player in player_results['data']:
        id = player['attributes']['game_id']
        if id not in game_player:
            game_player[id] = list()
        game_player[id].append(player)
    for game in game_results['data']:
        if game['id'] not in game_player:
            game['relationships'] = dict(players=dict(data=list()))
        else:
            game['relationships'] = dict(players=dict(data=list(game_player[game['id']])))

    return game_results


def throw_malformed_query_error(field):
    raise InvalidUsage('Invalid ' + field)
