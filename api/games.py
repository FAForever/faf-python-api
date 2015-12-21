from copy import copy
from faf.api.game_stats_schema import GameStatsSchema, GamePlayerStatsSchema
from faf.game_validity import GameValidity
from faf.victory_condition import VictoryCondition
from flask import request
from api import app
from api.query_commons import fetch_data

MAX_PAGE_SIZE = 1000

GAME_SELECT_EXPRESSIONS = {
    'id': 'id',
    'game_name': 'gameName',
    'map_id': 'mapId',
    'victory_condition': 'gameType',
    'game_mod': 'gameMod',
    'host': 'host',
    'start_time': 'startTime',
    'validity': 'validity'
}

PLAYER_SELECT_EXPRESSIONS = {
    'id': 'id',
    'player_id': 'playerId',
    'team': 'team',
    'faction': 'faction',
    'color': 'color',
    'has_ai': 'AI',
    'place': 'place',
    'mean': 'mean',
    'deviation': 'deviation',
    'score': 'score',
    'score_time': 'scoreTime'
}

GAME_STATS_TABLE = 'game_stats'
GAME_PLAYER_STATS_TABLE = 'game_player_stats'
TABLE_MAP_TABLE = 'table_map'
LOGIN_TABLE = 'login'
LADDER1V1_RATING_TABLE = 'ladder1v1_rating'

HEADER_EXPRESSION = 'game_player_stats gps INNER JOIN game_stats gs ON gs.id = gps.gameId'
FOOTER_EXPRESSION = ' GROUP BY gameId HAVING COUNT(*) > {}'

LOGIN_JOIN = ' INNER JOIN login l ON l.id = gps.playerId'
MAP_JOIN = ' INNER JOIN table_map tm ON tm.id = gs.mapId'
LADDER1V1_JOIN = ' INNER JOIN ladder1v1_rating lr ON lr.id = gps.playerId'

MAX_RATING_WHERE_EXPRESSION = '%s >= ROUND({}.mean - 3 * {}.deviation)'
MIN_RATING_WHERE_EXPRESSION = '%s <= ROUND({}.mean - 3 * {}.deviation)'
MAP_NAME_WHERE_EXPRESSION = 'tm.name = %s'
GAME_TYPE_WHERE_EXPRESSION = 'gs.gameType = %s'
AND = ' AND '
WHERE = ' WHERE '


@app.route('/games')
def games():
    if len(request.args) == 0:
        return fetch_data(GameStatsSchema(), GAME_STATS_TABLE, GAME_SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request,
                          enricher=enricher)

    player_list = request.args.get('filter[players]')
    map_name = request.args.get('filter[map_name]')
    max_rating = request.args.get('filter[max_rating]')
    min_rating = request.args.get('filter[min_rating]')
    game_type = request.args.get('filter[game_type]')
    rating_type = request.args.get('filter[rating_type]')

    select_expression, args = build_query(game_type, map_name, max_rating, min_rating, player_list, rating_type)

    modified_game_select_expression = copy(GAME_SELECT_EXPRESSIONS)
    modified_game_select_expression['id'] = "gs.id"

    return fetch_data(GameStatsSchema(), select_expression, modified_game_select_expression, MAX_PAGE_SIZE, request,
                      args=args, enricher=enricher)


@app.route('/games/<game_id>')
def game(game_id):
    game_result = fetch_data(GameStatsSchema(), GAME_STATS_TABLE, GAME_SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request,
                             where='id = %s', args=game_id, many=False, enricher=enricher)

    if 'id' not in game_result['data']:
        return {'errors': [{'title': 'No game with this game ID was found'}]}, 404

    player_results = fetch_data(GamePlayerStatsSchema(), GAME_PLAYER_STATS_TABLE, dict(id='id'), MAX_PAGE_SIZE,
                                request, where='gameId = %s', args=game_id)

    game_result['relationships'] = dict(players=player_results)

    return game_result


@app.route('/games/<game_id>/players')
def game_players(game_id):
    player_results = fetch_data(GamePlayerStatsSchema(), GAME_PLAYER_STATS_TABLE, PLAYER_SELECT_EXPRESSIONS,
                                MAX_PAGE_SIZE, request, where='gameId = %s', args=game_id)

    if not player_results['data']:
        return {'errors': [{'title': 'No players for this game ID were found'}]}, 404

    return player_results


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


def build_query(game_type=None, map_name=None, max_rating=None, min_rating=None, player_list=None, rating_type=None):
    table_expression = HEADER_EXPRESSION
    where_expression = ''
    args = list()
    first = True
    players = None

    if player_list:
        players = player_list.split(',')
        player_expression = LOGIN_TABLE + ' IN ({})'.format(','.join(['%s'] * len(players)))
        args += players
        table_expression += LOGIN_JOIN
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
        first, where_expression = append_where_expression(first, where_expression, MAP_NAME_WHERE_EXPRESSION)

    if game_type:
        args.append(game_type)
        first, where_expression = append_where_expression(first, where_expression, GAME_TYPE_WHERE_EXPRESSION)

    where_expression += FOOTER_EXPRESSION.format(len(players) - 1)
    return table_expression + where_expression, args


def build_rating_expression(rating, first, rating_type, table_expression,
                            where_expression, format_expression, args):
    if rating:
        try:
            rating = int(rating)
        except ValueError:
            return table_expression, where_expression, first

        if rating_type == 'ladder':
            if LADDER1V1_JOIN not in table_expression:
                table_expression += LADDER1V1_JOIN
            rating_expression = format_expression.format('lr', 'lr')
        else:
            rating_expression = format_expression.format('gps', 'gps')

        args.append(rating)
        first, where_expression = append_where_expression(first, where_expression, rating_expression)
    return table_expression, where_expression, args, first


def append_where_expression(first, where_expression, format_expression):
    if first:
        where_expression += WHERE + format_expression
        first = False
    else:
        where_expression += AND + format_expression
    return first, where_expression
