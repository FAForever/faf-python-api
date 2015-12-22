import distutils.util
from faf.api.game_stats_schema import GameStatsSchema, GamePlayerStatsSchema
from faf.game_validity import GameValidity
from faf.victory_condition import VictoryCondition
from flask import request
from api import app, InvalidUsage
from api.query_commons import fetch_data

MAX_PAGE_SIZE = 1000

GAME_SELECT_EXPRESSIONS = {
    'id': 'gs.id',
    'game_name': 'gameName',
    'map_id': 'mapId',
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

GAME_STATS_HEADER_EXPRESSION = 'game_player_stats gps INNER JOIN game_stats gs ON gs.id = gps.gameId'
GAME_STATS_FOOTER_EXPRESSION = ' GROUP BY gameId HAVING COUNT(*) > {}'
GAME_PLAYER_STATS_HEADER_EXPRESSION = 'game_player_stats gps {} {} WHERE gameId IN( SELECT gameId FROM '
GAME_PLAYER_STATS_FOOTER_EXPRESSION = ')'

LOGIN_JOIN = ' INNER JOIN login l ON l.id = gps.playerId'
MAP_JOIN = ' INNER JOIN table_map tm ON tm.id = gs.mapId'
GLOBAL_JOIN = ' INNER JOIN global_rating r ON r.id = gps.playerId'
LADDER1V1_JOIN = ' INNER JOIN ladder1v1_rating r ON r.id = gps.playerId'

MAX_RATING_WHERE_EXPRESSION = '%s >= ROUND(r.mean - 3 * r.deviation)'
MIN_RATING_WHERE_EXPRESSION = '%s <= ROUND(r.mean - 3 * r.deviation)'
MAP_NAME_WHERE_EXPRESSION = '{} tm.name = %s'
GAME_TYPE_WHERE_EXPRESSION = 'gs.gameType = %s'
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
    game_type = request.args.get('filter[game_type]')
    rating_type = request.args.get('filter[rating_type]')

    if rating_type and not (max_rating or min_rating):
        return {'errors': [{'title': 'missing max/min_rating parameters'}]}, 422

    if map_exclude and not map_name:
        return {'errors': [{'title': 'missing map_name parameter'}]}, 422

    if player_list or map_name or max_rating or min_rating or game_type:
        if not map_exclude:
            map_exclude = 'False'

        game_stats_select_expression, args = build_game_stats_query(game_type, map_name, map_exclude, max_rating,
                                                                    min_rating, player_list,
                                                                    rating_type)
        game_player_stats_select_expression = build_game_player_stats_query(game_stats_select_expression, rating_type)

        game_results = fetch_data(GameStatsSchema(), game_stats_select_expression, GAME_SELECT_EXPRESSIONS,
                                  MAX_PAGE_SIZE, request,
                                  args=args, enricher=enricher, sort='-id')
        player_results = fetch_data(GamePlayerStatsSchema(), game_player_stats_select_expression,
                                    PLAYER_SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request, args=args, sort='-game_id')
    else:
        game_results = fetch_data(GameStatsSchema(), GAME_STATS_TABLE, GAME_SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request,
                                  enricher=enricher, sort='-id')
        player_results = fetch_data(GamePlayerStatsSchema(), GAME_PLAYER_STATS_TABLE + GLOBAL_JOIN + LOGIN_JOIN,
                                    PLAYER_SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request, sort='-game_id')
    return join_game_and_player_results(game_results, player_results)


@app.route('/games/<game_id>')
def game(game_id):
    game_result = fetch_data(GameStatsSchema(), GAME_STATS_TABLE, GAME_SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request,
                             where='id = %s', args=game_id, many=False, enricher=enricher)

    if 'id' not in game_result['data']:
        return {'errors': [{'title': 'No game with this game ID was found'}]}, 404

    player_select_expression = GAME_PLAYER_STATS_TABLE + GLOBAL_JOIN
    player_results = fetch_data(GamePlayerStatsSchema(), player_select_expression, PLAYER_SELECT_EXPRESSIONS,
                                MAX_PAGE_SIZE,
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


def build_game_stats_query(game_type, map_name, map_exclude, max_rating, min_rating, player_list, rating_type):
    table_expression = GAME_STATS_HEADER_EXPRESSION + LOGIN_JOIN
    where_expression = ''
    args = list()
    first = True
    players = None

    if player_list:
        players = player_list.split(',')
        player_expression = LOGIN_TABLE + ' IN ({})'.format(','.join(['%s'] * len(players)))
        args += players
        first, where_expression = append_where_expression(first, where_expression, player_expression)

    table_expression, where_expression, args, first = build_rating_expression(max_rating, first, rating_type,
                                                                              table_expression, where_expression,
                                                                              MAX_RATING_WHERE_EXPRESSION, args)

    table_expression, where_expression, args, first = build_rating_expression(min_rating, first, rating_type,
                                                                              table_expression, where_expression,
                                                                              MIN_RATING_WHERE_EXPRESSION, args)

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

    if game_type:
        args.append(game_type)
        first, where_expression = append_where_expression(first, where_expression, GAME_TYPE_WHERE_EXPRESSION)

    if players:
        where_expression += GAME_STATS_FOOTER_EXPRESSION.format(len(players) - 1)
    else:
        where_expression += GAME_STATS_FOOTER_EXPRESSION.format(0)
    return table_expression + where_expression, args


def build_rating_expression(rating, first, rating_type, table_expression,
                            where_expression, rating_where_expression, args):
    if rating:
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
        first, where_expression = append_where_expression(first, where_expression, rating_where_expression)
    return table_expression, where_expression, args, first


def append_where_expression(first, where_expression, format_expression):
    if first:
        where_expression += WHERE + format_expression
        first = False
    else:
        where_expression += AND + format_expression
    return first, where_expression


def build_game_player_stats_query(game_stats_expression, rating_type):
    if rating_type == 'ladder':
        table_expression = GAME_PLAYER_STATS_HEADER_EXPRESSION.format(LADDER1V1_JOIN, LOGIN_JOIN)
    else:
        table_expression = GAME_PLAYER_STATS_HEADER_EXPRESSION.format(GLOBAL_JOIN, LOGIN_JOIN)
    return table_expression + game_stats_expression + GAME_PLAYER_STATS_FOOTER_EXPRESSION


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
