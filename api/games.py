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
    'after_mean': 'after_mean',
    'after_deviation': 'after_deviation',
    'score': 'score',
    'score_time': 'scoreTime'
}

GAME_STATS_TABLE = 'game_stats'
GAME_PLAYER_STATS_TABLE = 'game_player_stats'


@app.route('/games')
def games():
    return fetch_data(GameStatsSchema(), GAME_STATS_TABLE, GAME_SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request,
                      enricher=enricher)


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
