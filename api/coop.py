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
