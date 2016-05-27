import os
import urllib.parse

from faf.api import ModSchema
from flask import request
from werkzeug.utils import secure_filename

from api import app, InvalidUsage
from api.query_commons import fetch_data

ALLOWED_EXTENSIONS = {'zip'}
MAX_PAGE_SIZE = 1000

SELECT_EXPRESSIONS = {
    'id': 'uid',
    'name': 'name',
    'description': 'description',
    'version': 'version',
    'author': 'author',
    'is_ui': 'ui',
    'create_time': 'date',
    'downloads': 'downloads',
    'likes': 'likes',
    'times_played': 'played',
    'is_ranked': 'ranked',
    # download_url will be URL encoded and made absolute in enrich_mod
    'download_url': 'filename',
    # thumbnail_url will be URL encoded and made absolute in enrich_mod
    'thumbnail_url': 'icon'
}


@app.route('/mods/upload', methods=['POST'])
def mods_upload():
    """
    Creates a new mod in the system

    **Example Request**:

    .. sourcecode:: http

       POST /mods/upload

    **Example Response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: text/javascript

        "ok"

    :query file file: The file submitted (Must be ZIP)
    :type: zip

    """
    file = request.files.get('file')
    if not file:
        raise InvalidUsage("No file has been provided")

    if not file_allowed(file.filename):
        raise InvalidUsage("Invalid file extension")

    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['MOD_UPLOAD_PATH'], filename))
    return "ok"


@app.route('/mods/<mod_uid>')
def mod(mod_uid):
    """
    Gets a specific mod definition.

    **Example Request**:

    .. sourcecode:: http

       GET /mods/DF8825E2-DDB0-11DC-90F3-3F9B55D89593

    **Example Response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: text/javascript

        {
          "data": {
            "attributes": {
              "author": "Sorian(Current) Brent Allen(Original)",
              "create_time": "2014-04-05T17:13:18+00:00",
              "description": "Terrain is cratered by heavy ordinance.",
              "download_url": "http://content.faforever.com/faf/vault/mods/Terrain%20Deform%20for%20FA.v0001.zip",
              "downloads": 93,
              "id": "DF8825E2-DDB0-11DC-90F3-3F9B55D89593",
              "is_ranked": false,
              "is_ui": false,
              "likes": 1,
              "name": "Terrain Deform for FA",
              "version": "1"
            },
            "id": "DF8825E2-DDB0-11DC-90F3-3F9B55D89593",
            "type": "mod"
          }
        }


    """
    result = fetch_data(ModSchema(), 'table_mod', SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request,
                        where="`uid` = %s", args=mod_uid, many=False, enricher=enricher)

    if 'id' not in result['data']:
        return {'errors': [{'title': 'No mod with this uid was found'}]}, 404

    return result


@app.route('/mods')
def mods():
    """
    Lists all mod definitions.

    **Example Request**:

    .. sourcecode:: http

       GET /mods

    **Example Response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: text/javascript

        {
          "data": [
            {
              "attributes": {
                "author": "Sorian(Current) Brent Allen(Original)",
                "create_time": "2014-04-05T17:13:18+00:00",
                "description": "Terrain is cratered by heavy ordinance.",
                "download_url": "http://content.faforever.com/faf/vault/mods/Terrain%20Deform%20for%20FA.v0001.zip",
                "downloads": 93,
                "id": "DF8825E2-DDB0-11DC-90F3-3F9B55D89593",
                "is_ranked": false,
                "is_ui": false,
                "likes": 1,
                "name": "Terrain Deform for FA",
                "version": "1"
              },
              "id": "DF8825E2-DDB0-11DC-90F3-3F9B55D89593",
              "type": "mod"
            },
            ...
          ]
        }


    """
    return fetch_data(ModSchema(), 'table_mod', SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request, enricher=enricher)


def enricher(mod):
    if 'thumbnail_url' in mod:
        if not mod['thumbnail_url']:
            del mod['thumbnail_url']
        else:
            mod['thumbnail_url'] = '{}/faf/vault/mods_thumbs/{}'.format(app.config['CONTENT_URL'], mod['thumbnail_url'])

    if 'download_url' in mod:
        mod['download_url'] = '{}/faf/vault/{}'.format(app.config['CONTENT_URL'], urllib.parse.quote(mod['download_url']))


def file_allowed(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS
