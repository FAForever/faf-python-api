from faf.api.game_schema import *
from flask import request
from api import app
from api.query_commons import fetch_data

MAX_PAGE_SIZE = 1000

SELECT_GAME_EXPRESSIONS = {
    'id': 'id',
    'game_name': 'gameName',
    'mapId': 'mapId',
    'game_type': 'gameType',
    'game_mod': 'gameMod',
    'host': 'host',
    'start_time': 'startTime',
    'validity': 'validity'
}

SELECT_PLAYER_EXPRESSIONS = {
    'id': 'id',
    'player_id': 'playerId',
    'team': 'team',
    'faction': 'faction',
    'color': 'color',
    'ai': 'ai',
    'place': 'place',
    'mean': 'mean',
    'deviation': 'deviation',
    'after_mean': 'after_mean',
    'after_deviation': 'after_deviation',
    'score': 'score',
    'score_time': 'scoreTime'
}


@app.route('/games')
def games():
    result = fetch_data(GameStatsSchema(), 'game_stats', SELECT_GAME_EXPRESSIONS, MAX_PAGE_SIZE, request)

    # This should never happened unless something very bad happened
    if len(result['data']) == 0:
        return {'errors': [{'title': 'No games were found'}]}, 404

    return result


@app.route('/games/<game_id>')
def game(game_id):
    game_result = fetch_data(GameStatsSchema(), 'game_stats', SELECT_GAME_EXPRESSIONS, MAX_PAGE_SIZE, request,
                               where="id = %s", args=game_id, many=False)

    if 'id' not in game_result['data']:
        return {'errors': [{'title': 'No game with this game id was found'}]}, 404

    player_results = fetch_data(GamePlayerStatsSchema(), 'game_player_stats', dict(id="id"), MAX_PAGE_SIZE,
                                request, where="gameId = %s", args=game_id)

    game_result['relationships'] = dict(players=player_results)

    return game_result


@app.route('/games/<game_id>/players')
def game_players(game_id):
    player_results = fetch_data(GamePlayerStatsSchema(), 'game_player_stats', SELECT_PLAYER_EXPRESSIONS, MAX_PAGE_SIZE,
                                request, where="gameId = %s", args=game_id)

    if not player_results['data']:
        return {'errors': [{'title': 'No players for this game id was found'}]}, 404

    return player_results
