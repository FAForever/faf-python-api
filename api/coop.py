from faf.api.coop_leaderboard_schema import CoopLeaderboardSchema
from faf.api.coop_mission_schema import CoopMissionSchema
from flask import request

from api import app
from api.query_commons import fetch_data

import urllib.parse

SELECT_EXPRESSIONS = {
    'id': 'id',
    'category': "CASE type WHEN 0 THEN 'FA' WHEN 1 THEN 'AEON' WHEN 2 THEN 'CYBRAN' WHEN 3 THEN 'UEF' WHEN 4 THEN 'CUSTOM' END",
    'name': 'name',
    'version': 'version',
    'description': 'description',
    # download_url will be URL encoded and made absolute in enricher
    'download_url': "filename",
    # thumbnail_url_small will be URL encoded and made absolute in enricher
    'thumbnail_url_small': "REPLACE(REPLACE(filename, '.zip', '.png'), 'missions/', '')",
    # thumbnail_url_large will be URL encoded and made absolute in enricher
    'thumbnail_url_large': "REPLACE(REPLACE(filename, '.zip', '.png'), 'missions/', '')",
    'folder_name': "SUBSTRING(filename, LOCATE('/', filename)+1, LOCATE('.zip', filename)-6)"
}

LEADERBOARD_SELECT_EXPRESSIONS = {
    'id': 'leaderboard.id',
    'game_id': 'leaderboard.gameid',
    'player_names': 'leaderboard.player_names',
    'secondary_objectives': 'leaderboard.secondary',
    'duration': 'TIME_TO_SEC(leaderboard.time)',
    'ranking': '@rownum := @rownum + 1'
}

LEADERBOARD_BASE_TABLE = """
  (SELECT
    c.id,
    GROUP_CONCAT(login.login ORDER BY login SEPARATOR ', ') AS player_names,
    gameid,
    c.time,
    c.secondary,
    c.mission,
    c.player_count
   FROM (SELECT @rownum := 0) n,
    coop_leaderboard c
    INNER JOIN game_player_stats ON game_player_stats.gameid = c.gameuid
    INNER JOIN login ON game_player_stats.playerId = login.id
    WHERE mission = %(mission)s {}
  GROUP BY gameid
  ORDER BY time ASC) leaderboard
"""

LEADERBOARD_TABLE_BY_PLAYER_COUNT = LEADERBOARD_BASE_TABLE.format("AND player_count = %(player_count)s")
LEADERBOARD_TABLE_ALL = LEADERBOARD_BASE_TABLE.format("")

MAX_PAGE_SIZE = 1000


@app.route('/coop/missions')
def coop_missions():
    """
    Lists all coop missions.

    **Example Request**:

    .. sourcecode:: http

       GET /coop/missions

    **Example Response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: text/javascript

        {
          "data": [
            {
              "attributes": {
                "category": "CUSTOM",
                "description": "Prothyon - 16 is a secret UEF facillity for training new ACU pilots. Your task today is to provide a demonstration to our newest recruits by fighting against a training AI.",
                "download_url": "http://content.faforever.com/faf/vault/maps/prothyon16.v0006.zip",
                "id": "26",
                "name": "Prothyon - 16",
                "thumbnail_url_large": "http://content.faforever.com/faf/vault/map_previews/large/prothyon16.v0006.png",
                "thumbnail_url_small": "http://content.faforever.com/faf/vault/map_previews/small/prothyon16.v0006.png",
                "version": 6
              },
              "id": "26",
              "type": "coop_mission"
            },
            ...
          ]
        }


    """
    return fetch_data(CoopMissionSchema(), 'coop_map', SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request, enricher=enricher)


@app.route("/coop/leaderboards/<int:mission>/<int:player_count>")
def coop_leaderboards(mission, player_count):
    """
    Lists a coop leaderboard for a specific mission. `id` refers to the game id.

    **Example Request**:

    .. sourcecode:: http

       GET /coop/leaderboards

    **Example Response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: text/javascript

        {
          "data": [
            {
              "attributes": {
                "id": "112",
                "game_id": "1337",
                "ranking": 3,
                "player_names": "Someone, SomeoneElse",
                "secondary_objectives": true,
                "duration": 3600,
              },
              "id": "112",
              "type": "coop_leaderboard"
            },
            ...
          ]
        }


    """

    if player_count <= 0:
        table = LEADERBOARD_TABLE_ALL
    else:
        table = LEADERBOARD_TABLE_BY_PLAYER_COUNT

    return fetch_data(CoopLeaderboardSchema(), table, LEADERBOARD_SELECT_EXPRESSIONS,
                      MAX_PAGE_SIZE, request, args={'player_count': player_count, 'mission': mission},
                      enricher=enricher)


def enricher(mission):
    if 'thumbnail_url_small' in mission:
        if not mission['thumbnail_url_small']:
            del mission['thumbnail_url_small']
        else:
            mission['thumbnail_url_small'] = '{}/faf/vault/map_previews/small/{}'.format(
                app.config['CONTENT_URL'], urllib.parse.quote(mission['thumbnail_url_small']))

    if 'thumbnail_url_large' in mission:
        if not mission['thumbnail_url_large']:
            del mission['thumbnail_url_large']
        else:
            mission['thumbnail_url_large'] = '{}/faf/vault/map_previews/large/{}'.format(
                app.config['CONTENT_URL'], urllib.parse.quote(mission['thumbnail_url_large']))

    if 'download_url' in mission:
        mission['download_url'] = '{}/faf/vault/{}'.format(app.config['CONTENT_URL'],
                                                           urllib.parse.quote(mission['download_url']))
