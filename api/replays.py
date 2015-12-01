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
    result = fetch_data(ReplaySchema(), 'game_stats', SELECT_REPLAY_EXPRESSIONS, MAX_PAGE_SIZE, request)
    return result


@app.route('/replays/<replay_id>')
def replay(replay_id):
    replay_result = fetch_data(ReplaySchema(), 'game_stats', SELECT_REPLAY_EXPRESSIONS, MAX_PAGE_SIZE, request,
                               where="WHERE id = %s", args=replay_id, many=False)

    if 'id' not in replay_result['data']:
        return {'errors': [{'title': 'No replay with this uid was found'}]}, 404

    player_results = fetch_data(PlayerReplaySchema(), 'game_player_stats', SELECT_PLAYER_EXPRESSIONS, MAX_PAGE_SIZE,
                                request, where="WHERE gameId = %s", args=replay_id)

    player_list = [player['attributes'] for player in player_results['data']]
    replay_result['data']['attributes']['players'] = player_list

    return replay_result