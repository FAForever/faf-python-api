from dateutil.parser import parse
from dateutil.tz import tzoffset
from faf.api.game_stats_schema import GameStatsSchema, GamePlayerStatsSchema
from faf.game_validity import GameValidity
from faf.victory_condition import VictoryCondition
from flask import request
from api import app, InvalidUsage
from api.query_commons import fetch_data, get_page_attributes, get_limit

MAX_GAME_PAGE_SIZE = 1000
MAX_PLAYER_PAGE_SIZE = MAX_GAME_PAGE_SIZE * 12

GAME_STATS_TABLE = 'game_stats gs'
GAME_PLAYER_STATS_TABLE = 'game_player_stats gps'

GAME_PLAYER_STATS_JOIN = ' INNER JOIN game_player_stats gps ON gs.id = gps.gameId'
MAP_JOIN = ' INNER JOIN table_map tm ON tm.id = gs.mapId'
LOGIN_JOIN = ' INNER JOIN login l ON l.id = gps.playerId'
GLOBAL_JOIN = ' INNER JOIN global_rating r ON r.id = gps.playerId'
LADDER1V1_JOIN = ' INNER JOIN ladder1v1_rating r ON r.id = gps.playerId'

GAMES_NO_FILTER_EXPRESSION = GAME_PLAYER_STATS_TABLE + ' INNER JOIN (SELECT * FROM ' + GAME_STATS_TABLE + ' {})' \
                                                                                                          ' AS gs ON gs.id = gps.gameId' + LOGIN_JOIN + MAP_JOIN + GLOBAL_JOIN

PLAYER_COUNT_EXPRESSION = '(SELECT COUNT(*) FROM ' + GAME_PLAYER_STATS_TABLE + ' WHERE gs.id = gps.gameId)'
RATING_EXPRESSION = '(ROUND(r.mean-3*r.deviation)) FROM ' + GAME_PLAYER_STATS_TABLE + ' {} WHERE gps.gameId=gs.id)'
MIN_RATING_HEADER_EXPRESSION = '(SELECT MIN'
MAX_RATING_HEADER_EXPRESSION = '(SELECT MAX'
HEADER = GAME_STATS_TABLE + GAME_PLAYER_STATS_JOIN + LOGIN_JOIN + MAP_JOIN + '{}'
SUBQUERY_HEADER = ' WHERE gs.id IN (SELECT * FROM (SELECT {} FROM '
SUBQUERY_FOOTER = '{}) as games)'

GROUP_BY_EXPRESSION = ' GROUP BY gameId HAVING COUNT(*) > {} '
MAP_NAME_WHERE_EXPRESSION = '{} tm.name = %s'
MAX_PLAYER_WHERE_EXPRESSION = 'player_count <= %s'
MIN_PLAYER_WHERE_EXPRESSION = 'player_count >= %s'
VICTORY_CONDITION_WHERE_EXPRESSION = 'gs.gameType = %s'
MAX_RATING_HAVING_EXPRESSION = 'max_rating <= %s'
MIN_RATING_HAVING_EXPRESSION = 'min_rating >= %s'
MAX_DATE_HAVING_EXPRESSION = 'startTime <= %s'
MIN_DATE_HAVING_EXPRESSION = 'startTime >= %s'

LIMIT = ' LIMIT '
AND = ' AND '
WHERE = ' WHERE '
HAVING = ' HAVING '
NOT = ' NOT'

GAME_SELECT_EXPRESSIONS = {
    'id': 'gs.id',
    'game_name': 'gameName',
    'map_name': 'tm.name',
    'victory_condition': 'gameType',
    'game_mod': 'gameMod',
    'host': 'host',
    'start_time': 'startTime',
    'validity': 'validity',
    'player_count': PLAYER_COUNT_EXPRESSION
}

PLAYER_SELECT_EXPRESSIONS = {
    'id': 'gps.id',
    'game_id': 'gameId',
    'player_id': 'playerId',
    'login': 'l.login',
    'team': 'team',
    'faction': 'faction',
    'color': 'color',
    'is_ai': 'AI',
    'place': 'place',
    'mean': 'r.mean',
    'deviation': 'r.deviation',
    'score': 'score',
    'score_time': 'scoreTime'
}

GAME_AND_PLAYER_SELECT_EXPRESSIONS = {**GAME_SELECT_EXPRESSIONS, **PLAYER_SELECT_EXPRESSIONS}
UTC_TZ = tzoffset('UTC', 0)


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
    max_datetime = request.args.get('filter[max_datetime]')
    min_datetime = request.args.get('filter[min_datetime]')

    page, page_size = get_page_attributes(MAX_GAME_PAGE_SIZE, request)
    limit_expression = get_limit(page, page_size)

    errors = check_syntax_errors(rating_type, max_rating, min_rating, map_exclude, map_name, max_datetime, min_datetime)
    if errors:
        return errors

    if player_list or map_name or max_rating or min_rating or victory_condition or max_players or min_players \
            or max_datetime or min_datetime:
        select_expression, args = build_query(victory_condition, map_name, map_exclude, max_rating, min_rating,
                                              player_list, rating_type, max_players, min_players, max_datetime,
                                              min_datetime, limit_expression)

        game_player_joined_maps = GAME_AND_PLAYER_SELECT_EXPRESSIONS
        game_player_joined_maps['max_rating'] = build_rating_selector(rating_type, MAX_RATING_HEADER_EXPRESSION)
        game_player_joined_maps['min_rating'] = build_rating_selector(rating_type, MIN_RATING_HEADER_EXPRESSION)

        result = fetch_data(GameStatsSchema(), select_expression, game_player_joined_maps,
                            MAX_PLAYER_PAGE_SIZE, request, args=args, sort='-id', item_enricher=enricher)
    else:
        result = fetch_data(GameStatsSchema(), GAMES_NO_FILTER_EXPRESSION.format(limit_expression),
                            GAME_AND_PLAYER_SELECT_EXPRESSIONS, MAX_PLAYER_PAGE_SIZE, request, sort='-id',
                            item_enricher=enricher)

    return sort_player_game_results(result)


@app.route('/games/<game_id>')
def game(game_id):
    result = fetch_data(GameStatsSchema(),
                        GAME_STATS_TABLE + MAP_JOIN + GAME_PLAYER_STATS_JOIN + GLOBAL_JOIN + LOGIN_JOIN,
                        GAME_AND_PLAYER_SELECT_EXPRESSIONS, MAX_GAME_PAGE_SIZE, request,
                        where='gs.id = %s', args=game_id, item_enricher=enricher)

    if len(result['data']) == 0:
        return {'errors': [{'title': 'No game with this game ID was found'}]}, 404

    return sort_player_game_results(result)


# @app.route('/games/<game_id>/players')
# def game(game_id):
#     result = fetch_data(GameStatsSchema(),
#                         GAME_STATS_TABLE + MAP_JOIN + GAME_PLAYER_STATS_JOIN + GLOBAL_JOIN + LOGIN_JOIN,
#                         GAME_AND_PLAYER_SELECT_EXPRESSIONS, MAX_GAME_PAGE_SIZE, request,
#                         where='gs.id = %s', args=game_id, enricher=enricher)
#
#     if len(result['data']) == 0:
#         return {'errors': [{'title': 'No game with this game ID was found'}]}, 404
#
#     return sort_player_game_results(result)


@app.route('/games/<game_id>/relationships/players')
def game_players(game_id):
    player_results = fetch_data(GamePlayerStatsSchema(), GAME_PLAYER_STATS_TABLE + LOGIN_JOIN + GLOBAL_JOIN,
                                PLAYER_SELECT_EXPRESSIONS,
                                MAX_GAME_PAGE_SIZE, request, where='gameId = %s', args=game_id)

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
    # attributes = GamePlayerStatsSchema(**{key: game[key] for key in PLAYER_SELECT_EXPRESSIONS.keys() if key in game})
    # game['players'] = attributes


def check_syntax_errors(rating_type, max_rating, min_rating, map_exclude, map_name, max_datetime, min_datetime):
    if rating_type and not (max_rating or min_rating):
        return {'errors': [{'title': 'Missing max/min_rating parameters'}]}, 422
    elif map_exclude and not map_name:
        return {'errors': [{'title': 'Missing map_name parameter'}]}, 422
    try:
        if max_datetime and not parse(max_datetime).tzinfo:
            return {'errors': [{'title': 'max date time must include timezone'}]}, 422
        if min_datetime and not parse(min_datetime).tzinfo:
            return {'errors': [{'title': 'min date time must include timezone'}]}, 422
    except ValueError:
        throw_malformed_query_error('date time')
    return None


def build_query(victory_condition, map_name, map_exclude, max_rating, min_rating, player_list, rating_type, max_players,
                min_players, max_datetime, min_datetime, limit_expression):
    table_expression = HEADER
    having_expression = ''
    first = True

    subquery_expression, args = build_subquery(victory_condition, map_name, map_exclude, player_list, limit_expression)

    table_expression = format_with_rating(rating_type, table_expression)
    if max_rating or min_rating:
        having_expression, args, first = build_rating_expression(first, having_expression, args,
                                                                 (max_rating, MAX_RATING_HAVING_EXPRESSION),
                                                                 (min_rating, MIN_RATING_HAVING_EXPRESSION))

    if max_players or min_players:
        having_expression, args, first = build_player_count_expression(first, having_expression, args,
                                                                       (max_players, MAX_PLAYER_WHERE_EXPRESSION),
                                                                       (min_players, MIN_PLAYER_WHERE_EXPRESSION))

    if max_datetime or min_datetime:
        having_expression, args, first = build_date_time_expression(first, having_expression, args,
                                                                    (max_datetime, MAX_DATE_HAVING_EXPRESSION),
                                                                    (min_datetime, MIN_DATE_HAVING_EXPRESSION))

    return table_expression + subquery_expression + having_expression, args


def build_subquery(victory_condition, map_name, map_exclude, player_list, limit_expression):
    table_expression = SUBQUERY_HEADER
    where_expression = ''
    args = list()
    first = True
    players = None

    if not (victory_condition or map_name or player_list):
        return '', args

    if map_name or victory_condition:
        table_expression = table_expression.format('gs.id') + GAME_STATS_TABLE
        if player_list:
            table_expression += GAME_PLAYER_STATS_JOIN
    else:
        table_expression = table_expression.format('gameId') + GAME_PLAYER_STATS_TABLE

    if player_list:
        table_expression += LOGIN_JOIN
        players = player_list.split(',')
        player_expression = 'l.login IN ({})'.format(','.join(['%s'] * len(players)))
        first, where_expression, args = append_filter_expression(WHERE, first, where_expression, player_expression,
                                                                 args, *players)

    if map_name:
        table_expression += MAP_JOIN
        if map_exclude:
            map_name_expression = MAP_NAME_WHERE_EXPRESSION.format(NOT)
        else:
            map_name_expression = MAP_NAME_WHERE_EXPRESSION.format('')

        first, where_expression, args = append_filter_expression(WHERE, first, where_expression, map_name_expression,
                                                                 args, map_name)

    if victory_condition:
        condition = VictoryCondition.from_gpgnet_string(victory_condition)
        # condition can return a falsey value of 0
        if condition is not None:
            first, where_expression, args = append_filter_expression(WHERE, first, where_expression,
                                                                     VICTORY_CONDITION_WHERE_EXPRESSION,
                                                                     args, str(condition.value))
        else:
            throw_malformed_query_error('victory_condition')

    if players:
        where_expression += GROUP_BY_EXPRESSION.format(len(players) - 1)

    table_expression += where_expression + SUBQUERY_FOOTER.format(limit_expression)

    return table_expression, args


def build_rating_selector(rating_type, rating_expression):
    if rating_type == 'ladder':
        return rating_expression + RATING_EXPRESSION.format(LADDER1V1_JOIN)
    else:
        return rating_expression + RATING_EXPRESSION.format(GLOBAL_JOIN)


def format_with_rating(rating_type, expression):
    if rating_type == 'ladder':
        expression = expression.format(LADDER1V1_JOIN)
    else:
        expression = expression.format(GLOBAL_JOIN)
    return expression


def build_rating_expression(first, having_expression, args, *rating_bounds):
    for rating, rating_bound_expression in rating_bounds:
        if not rating:
            continue
        try:
            rating = int(rating)
        except ValueError:
            throw_malformed_query_error('rating field')
        first, where_expression, args = append_filter_expression(HAVING, first, '', rating_bound_expression, args,
                                                                 rating)
        having_expression += where_expression

    return having_expression, args, first


def build_player_count_expression(first, table_expression, args, *player_counts):
    for player_count, count_expression in player_counts:
        if not player_count:
            continue
        try:
            player_count = int(player_count)
        except ValueError:
            throw_malformed_query_error('player count field')

        first, table_expression, args = append_filter_expression(HAVING, first, table_expression, count_expression,
                                                                 args,
                                                                 player_count)

    return table_expression, args, first


def build_date_time_expression(first, having_expression, args, *date_times):
    for date_time, date_expression in date_times:
        if not date_time:
            continue
        converted_dt = parse(date_time).astimezone(UTC_TZ)
        first, having_expression, args = append_filter_expression(HAVING, first, having_expression, date_expression,
                                                                  args, converted_dt)

    return having_expression, args, first


def append_filter_expression(prefix, first, where_expression, format_expression, args, *new_args):
    if first:
        where_expression += prefix + format_expression
        first = False
    else:
        where_expression += AND + format_expression
    args.extend(new_args)
    return first, where_expression, args


def sort_player_game_results(results):
    game_player = dict(data=list())
    data = game_player['data']

    current_relationships = None
    current_game_id = None
    for game_player_object in results['data']:
        game_id = game_player_object['id']
        game_player_attributes = game_player_object['attributes']
        if current_game_id != game_id:
            current_game_id = game_id
            gs_type = game_player_object['type']
            attributes = {key: game_player_attributes[key] for key in GAME_SELECT_EXPRESSIONS.keys() if
                          key in game_player_attributes}
            current_relationships = dict(players=dict(data=list()))
            data.append(dict(id=game_id, type=gs_type, attributes=attributes, relationships=current_relationships))
        player_dict = {key: game_player_attributes[key] for key in PLAYER_SELECT_EXPRESSIONS.keys() if
                       key in game_player_attributes}

        player_object = dict(attributes=player_dict)
        current_relationships['players']['data'].append(player_object)
        player_object['type'] = 'game_player_stats'

        # TODO when id is removed from attributes for all other routes fix this line
        if 'game_player_stats_id' in player_dict:
            player_object['id'] = player_dict.pop('game_player_stats_id')
    return game_player


def throw_malformed_query_error(field):
    raise InvalidUsage('Invalid ' + field)
