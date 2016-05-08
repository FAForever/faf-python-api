from faf.api.game_stats_schema import GameStats
from faf.game_validity import GameValidity
from faf.victory_condition import VictoryCondition
from flask import request
from api import app, InvalidUsage
from api.query_commons import fetch_data, get_page_attributes, get_limit
from iso8601 import parse_date, ParseError

MAX_GAME_PAGE_SIZE = 1000
MAX_PLAYER_PAGE_SIZE = MAX_GAME_PAGE_SIZE * 16

GAME_STATS_TABLE = 'game_stats gs'
GAME_PLAYER_STATS_TABLE = 'game_player_stats gps'

GAME_PLAYER_STATS_JOIN = ' INNER JOIN game_player_stats gps ON gs.id = gps.gameId'
MAP_JOIN = ' INNER JOIN table_map tmap ON tmap.id = gs.mapId'
FEATURED_MOD_JOIN = ' INNER JOIN game_featuredMods gfmod ON gfmod.id = gs.gameMod'
LOGIN_JOIN = ' INNER JOIN login l ON l.id = gps.playerId'
GLOBAL_JOIN = ' INNER JOIN global_rating r ON r.id = gps.playerId'
LADDER1V1_JOIN = ' INNER JOIN ladder1v1_rating r ON r.id = gps.playerId'

PLAYER_COUNT_EXPRESSION = '(SELECT COUNT(*) FROM ' + GAME_PLAYER_STATS_TABLE + ' WHERE gs.id = gps.gameId)'
RATING_EXPRESSION = '(ROUND(r.mean-3*r.deviation)) FROM ' + GAME_PLAYER_STATS_TABLE + ' {} WHERE gps.gameId=gs.id)'
MIN_RATING_HEADER_EXPRESSION = '(SELECT MIN'
MAX_RATING_HEADER_EXPRESSION = '(SELECT MAX'
HEADER = GAME_STATS_TABLE + GAME_PLAYER_STATS_JOIN + LOGIN_JOIN + MAP_JOIN + FEATURED_MOD_JOIN + '{}'
SUBQUERY_HEADER = ' WHERE gs.id IN (SELECT * FROM (SELECT {} FROM {}'
SUBQUERY_ORDER_BY = ' ORDER BY {} DESC'
SUBQUERY_FOOTER = ' {}) AS games)'

GROUP_BY_EXPRESSION = ' GROUP BY gameId HAVING COUNT(*) > {} '
MAP_NAME_WHERE_EXPRESSION = '{} tmap.name = %s'
MAX_PLAYER_WHERE_EXPRESSION = 'player_count <= %s'
MIN_PLAYER_WHERE_EXPRESSION = 'player_count >= %s'
VICTORY_CONDITION_WHERE_EXPRESSION = 'gs.gameType = %s'
GAME_MOD_WHERE_EXPRESSION = '{}.{} = %s'
GAME_MOD_WHERE_ID = 'gs', 'gameMod'
GAME_MOD_WHERE_NAME = 'gfmod', 'name'
MAX_RATING_HAVING_EXPRESSION = 'max_rating <= %s'
MIN_RATING_HAVING_EXPRESSION = 'min_rating >= %s'
MAX_DATE_HAVING_EXPRESSION = 'startTime <= %s'
MIN_DATE_HAVING_EXPRESSION = 'startTime >= %s'

GAMES_NO_FILTER_EXPRESSION = GAME_PLAYER_STATS_TABLE + ' INNER JOIN (SELECT * FROM ' + GAME_STATS_TABLE + \
                             SUBQUERY_ORDER_BY + ' {}) AS gs ON gs.id = gps.gameId' \
                             + LOGIN_JOIN + MAP_JOIN + FEATURED_MOD_JOIN + GLOBAL_JOIN

AND = ' AND '
WHERE = ' WHERE '
HAVING = ' HAVING '
NOT = ' NOT'

GAME_SELECT_EXPRESSIONS = {
    'id': 'gs.id',
    'game_name': 'gameName',
    'map_name': 'tmap.name',
    'map_id': 'tmap.id',
    'victory_condition': 'gameType',
    'mod_name': 'gfmod.gamemod',
    'mod_id': 'gfmod.id',
    'host': 'host',
    'start_time': 'startTime',
    'validity': 'validity',
    'player_count': PLAYER_COUNT_EXPRESSION
}

PLAYER_SELECT_EXPRESSIONS = {
    'game_id': 'gameId',
    'player_id': 'playerId',
    'login': 'l.login',
    'team': 'team',
    'faction': 'faction',
    'color': 'color',
    'is_ai': 'AI',
    'place': 'place',
    'mean': 'r.mean',
    'max_rating': 'NULL',
    'min_rating': 'NULL',
    'deviation': 'r.deviation',
    'score': 'score',
    'score_time': 'scoreTime'
}


@app.route('/games')
def games():
    """Searches for games.

    HTTP Parameters::
        Field                Type              Description

        players              string            A comma delimited list of the players to search for
        map_name             string            The map name to search for
        map_exclude          string            If any input is provided, map provided in map_name is excluded instead of included, requires map_name
        max_rating           integer           Inclusive maximum rating bound for all players
        min_rating           integer           Inclusive minimum rating bound for all players
        victory_condition    string/integer    The victory condition to search for, can be either id or name
        mod                  string/integer    The featured mod to search for, can be either id or name
        rating_type          string            Rating type to search for, defaults to global, else `ladder` must be provided for ladder rating
        max_player_count     integer           Inclusive maximum player count bound, uses rating_type value
        min_player_count     integer           Inclusive minimum player count bound, uses rating_type value
        max_datetime         string            Inclusive latest datetime (iso8601 format), based on game start time
        min_datetime         string            Inclusive earliest datetime (iso8601 format), based on game start time

    :return:
        If successful, this method returns a response body with the following structure::

            {
              "data": [
                {
                  "attributes": {
                    "game_name": string,
                    "host": string,
                    "id": string,
                    "map_id": integer,
                    "map_name": string,
                    "mod_id": integer,
                    "mod_name": string,
                    "players": [
                      {
                        "color": integer,
                        "deviation": float,
                        "faction": string,
                        "is_ai": boolean,
                        "login": string,
                        "mean": float,
                        "place": integer,
                        "player_id": string,
                        "score": integer,
                        "score_time": string,
                        "team": integer
                      }
                    ],
                    "start_time": string,
                    "validity": string,
                    "victory_condition": string
                  }
                ]
                "id": string,
                "type": strings
              }
    """

    player_list = request.args.get('filter[players]')
    map_name = request.args.get('filter[map_name]')
    map_exclude = request.args.get('filter[map_exclude]')
    max_rating = request.args.get('filter[max_rating]')
    min_rating = request.args.get('filter[min_rating]')
    victory_condition = request.args.get('filter[victory_condition]')
    game_mod = request.args.get('filter[mod]')
    rating_type = request.args.get('filter[rating_type]')
    max_players = request.args.get('filter[max_player_count]')
    min_players = request.args.get('filter[min_player_count]')
    max_datetime = request.args.get('filter[max_datetime]')
    min_datetime = request.args.get('filter[min_datetime]')

    page, page_size = get_page_attributes(MAX_PLAYER_PAGE_SIZE, request)
    limit_expression = get_limit(page, page_size)

    errors = check_syntax_errors(map_exclude, map_name, max_datetime, min_datetime)
    if errors:
        return errors

    if player_list or map_name or max_rating or min_rating or rating_type or victory_condition or game_mod \
            or max_players or min_players or max_datetime or min_datetime:
        select_expression, args, limit = build_query(victory_condition, map_name, map_exclude, max_rating, min_rating,
                                                     player_list, rating_type, max_players, min_players, max_datetime,
                                                     min_datetime, game_mod, limit_expression)

        player_select_expression = PLAYER_SELECT_EXPRESSIONS
        player_select_expression['max_rating'] = build_rating_selector(rating_type, MAX_RATING_HEADER_EXPRESSION)
        player_select_expression['min_rating'] = build_rating_selector(rating_type, MIN_RATING_HEADER_EXPRESSION)

        result = fetch_data(GameStats(), select_expression, GAME_SELECT_EXPRESSIONS,
                            MAX_PLAYER_PAGE_SIZE, request, args=args, sort='-id', enricher=enricher, limit=limit,
                            players=player_select_expression)
    else:
        result = fetch_data(GameStats(),
                            GAMES_NO_FILTER_EXPRESSION.format('gs.id', limit_expression),
                            GAME_SELECT_EXPRESSIONS, MAX_PLAYER_PAGE_SIZE, request, sort='-id', enricher=enricher,
                            limit=False, players=PLAYER_SELECT_EXPRESSIONS)
    return sort_game_results(result)


@app.route('/games/<game_id>')
def game(game_id):
    result = fetch_data(GameStats(),
                        GAME_STATS_TABLE + MAP_JOIN + GAME_PLAYER_STATS_JOIN + GLOBAL_JOIN + LOGIN_JOIN +
                        FEATURED_MOD_JOIN, GAME_SELECT_EXPRESSIONS, MAX_GAME_PAGE_SIZE, request,
                        where='gs.id = %s', args=game_id, enricher=enricher, players=PLAYER_SELECT_EXPRESSIONS)

    if len(result['data']) == 0:
        return {'errors': [{'title': 'No game with this game ID was found'}]}, 404

    return sort_game_results(result)


def enricher(game):
    if 'victory_condition' in game:
        game['victory_condition'] = VictoryCondition(int(game['victory_condition'])).name

    if 'validity' in game:
        game['validity'] = GameValidity(int(game['validity'])).name


def check_syntax_errors(map_exclude, map_name, max_datetime, min_datetime):
    if map_exclude and not map_name:
        return {'errors': [{'title': 'Missing map_name parameter'}]}, 422
    try:
        if max_datetime and not parse_date(max_datetime).tzinfo:
            return {'errors': [{'title': 'max date time must include timezone'}]}, 422
        if min_datetime and not parse_date(min_datetime).tzinfo:
            return {'errors': [{'title': 'min date time must include timezone'}]}, 422
    except ParseError:
        throw_malformed_query_error('date time')
    return None


def build_query(victory_condition, map_name, map_exclude, max_rating, min_rating, player_list, rating_type, max_players,
                min_players, max_datetime, min_datetime, game_mod, limit_expression):
    table_expression = HEADER
    having_expression = ''
    first = True

    subquery_expression, args, limit = build_subquery(victory_condition, map_name, map_exclude,
                                                      player_list, game_mod, limit_expression)

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

    return table_expression + subquery_expression + having_expression, args, limit


def build_subquery(victory_condition, map_name, map_exclude, player_list, game_mod, limit_expression):
    table_expression = SUBQUERY_HEADER
    where_expression = ''
    args = []
    first = True
    players = None

    if not (victory_condition or map_name or player_list or game_mod):
        return '', args, True

    if map_name or victory_condition or game_mod:
        table_expression = table_expression.format('gs.id', GAME_STATS_TABLE)
        order_by_expression = SUBQUERY_ORDER_BY.format('gs.id')
        if player_list:
            table_expression += GAME_PLAYER_STATS_JOIN
    else:
        table_expression = table_expression.format('gameId', GAME_PLAYER_STATS_TABLE, '')
        order_by_expression = SUBQUERY_ORDER_BY.format('gameId')

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
        condition = victory_condition
        if not victory_condition.isdigit():
            condition = VictoryCondition.from_gpgnet_string(victory_condition)
            # condition can return a falsey value of 0
            if condition is not None:
                condition = condition.value
            else:
                throw_malformed_query_error('victory_condition')
        first, where_expression, args = append_filter_expression(WHERE, first, where_expression,
                                                                 VICTORY_CONDITION_WHERE_EXPRESSION,
                                                                 args, str(condition))

    if game_mod:
        if game_mod.isdigit():
            game_mod_expression = GAME_MOD_WHERE_EXPRESSION.format(*GAME_MOD_WHERE_ID)
        else:
            game_mod_expression = GAME_MOD_WHERE_EXPRESSION.format(*GAME_MOD_WHERE_NAME)
            table_expression += FEATURED_MOD_JOIN
        first, where_expression, args = append_filter_expression(WHERE, first, where_expression,
                                                                 game_mod_expression,
                                                                 args, game_mod)

    if players:
        where_expression += GROUP_BY_EXPRESSION.format(len(players) - 1)

    table_expression += where_expression + order_by_expression + SUBQUERY_FOOTER.format(limit_expression)

    return table_expression, args, False


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
        converted_dt = parse_date(date_time)
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


def sort_game_results(results):
    game_player = {'data': []}
    data = game_player['data']

    current_game_attributes = None
    current_game_id = None
    for game_result in results['data']:
        game_id = game_result['id']
        game_attributes = game_result['attributes']
        if current_game_id != game_id:
            current_game_id = game_id
            gs_type = game_result['type']
            current_game_attributes = {key: game_attributes[key] for key in GAME_SELECT_EXPRESSIONS.keys() if
                                       key in game_attributes}
            if any(x in game_attributes for x in PLAYER_SELECT_EXPRESSIONS.keys()):
                current_game_attributes['players'] = []
            data.append({'id': game_id, 'type': gs_type, 'attributes': current_game_attributes})
        if 'players' in current_game_attributes:
            player_dict = {key: game_attributes[key] for key in PLAYER_SELECT_EXPRESSIONS.keys() if
                           key in game_attributes}
            player_dict.pop('game_id', None)
            if player_dict:
                current_game_attributes['players'].append(player_dict)
    return game_player


def throw_malformed_query_error(field):
    raise InvalidUsage('Invalid ' + field)
