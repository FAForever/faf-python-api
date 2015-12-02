from faf.api.replay_schema import *
from flask import request
from api import app
from api.query_commons import fetch_data

MAX_PAGE_SIZE = 1000

SELECT_REPLAY_EXPRESSIONS = {
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


@app.route('/replays')
def replays():
    result = fetch_data(GameStatsSchema(), 'game_stats', SELECT_REPLAY_EXPRESSIONS, MAX_PAGE_SIZE, request)

    # This should never happened unless something very bad happened
    if len(result['data']) == 0:
        return {'errors': [{'title': 'No replays were found'}]}, 404

    return result


@app.route('/replays/<replay_id>')
def replay(replay_id):
    replay_result = fetch_data(GameStatsSchema(), 'game_stats', SELECT_REPLAY_EXPRESSIONS, MAX_PAGE_SIZE, request,
                               where="id = %s", args=replay_id, many=False)

    if 'id' not in replay_result['data']:
        return {'errors': [{'title': 'No replay with this replay id was found'}]}, 404

    player_results = fetch_data(GamePlayerStatsSchema(), 'game_player_stats', dict(id="id"), MAX_PAGE_SIZE,
                                request, where="gameId = %s", args=replay_id)

    replay_result['relationships'] = dict(players=player_results)

    return replay_result


@app.route('/replays/<replay_id>/players')
def replay_players(replay_id):
    player_results = fetch_data(GamePlayerStatsSchema(), 'game_player_stats', SELECT_PLAYER_EXPRESSIONS, MAX_PAGE_SIZE,
                                request, where="gameId = %s", args=replay_id)

    if not player_results['data']:
        return {'errors': [{'title': 'No players for this replay id was found'}]}, 404

    return player_results
