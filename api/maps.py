import json
import logging
import os
import shutil
import tempfile
import urllib.parse

from faf.api.map_schema import MapSchema
from faf.tools.fa.maps import generate_map_previews, parse_map_info, generate_folder_name, generate_zip
from flask import request
from pathlib import Path
from werkzeug.utils import secure_filename

from api import app, oauth
from api.error import ApiException, Error, ErrorCode
from api.query_commons import fetch_data
from faf import db

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = ['zip']
MAX_PAGE_SIZE = 1000

SELECT_EXPRESSIONS = {
    'id': 'map.id',
    'display_name': 'map.display_name',
    'description': 'version.description',
    'max_players': 'version.max_players',
    'map_type': 'map.map_type',
    'battle_type': 'map.battle_type',
    'width': 'version.width',
    'height': 'version.height',
    'author': 'l.login',
    'version': 'version.version',
    'ranked': "IF(version.ranked > 0, 'true', 'false')",
    # download_url will be URL encoded and made absolute in enricher
    'download_url': "version.filename",
    # thumbnail_url_small will be URL encoded and made absolute in enricher
    'thumbnail_url_small': "REPLACE(REPLACE(version.filename, '.zip', '.png'), 'maps/', '')",
    # thumbnail_url_large will be URL encoded and made absolute in enricher
    'thumbnail_url_large': "REPLACE(REPLACE(version.filename, '.zip', '.png'), 'maps/', '')",
    'technical_name': "SUBSTRING(version.filename, LOCATE('/', version.filename)+1, LOCATE('.zip', version.filename)-6)",
    'downloads': 'COALESCE(features.downloads, 0)',
    'num_draws': 'COALESCE(features.num_draws, 0)',
    'rating': 'features.rating',
    'times_played': 'COALESCE(features.times_played, 0)',
    'create_time': 'version.create_time'
}

TABLE = 'map ' \
        'LEFT JOIN table_map_features features ON features.map_id = map.id ' \
        'JOIN map_version version ON version.map_id = map.id ' \
        'LEFT JOIN login l ON l.id = map.author'


@app.route('/maps/upload', methods=['POST'])
@oauth.require_oauth('upload_map')
def maps_upload():
    """
    Creates a new map in the system

    **Example Request**:

    .. sourcecode:: http

       POST /maps/upload

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
    metadata_string = request.form.get('metadata')

    if not file:
        raise ApiException([Error(ErrorCode.UPLOAD_FILE_MISSING)])

    if not metadata_string:
        raise ApiException([Error(ErrorCode.UPLOAD_METADATA_MISSING)])

    if not file_allowed(file.filename):
        raise ApiException([Error(ErrorCode.UPLOAD_INVALID_FILE_EXTENSION, *ALLOWED_EXTENSIONS)])

    metadata = json.loads(metadata_string)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_map_path = os.path.join(temp_dir, secure_filename(file.filename))
        file.save(temp_map_path)
        process_uploaded_map(temp_map_path, metadata.get('is_ranked', False))

    return "ok"


@app.route('/maps')
def maps():
    """
    Lists all map definitions.

    **Example Request**:

    .. sourcecode:: http

       GET /maps

    **Example Response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: text/javascript

        {
          "data": [
            {
              "attributes": {
                "battle_type": "FFA",
                "description": "<LOC canis3v3_Description>",
                "display_name": "canis3v3",
                "download_url": "http://content.faforever.com/faf/vault/maps/canis3v3.v0001.zip",
                "downloads": 5970,
                "id": 0,
                "map_type": "skirmish",
                "max_players": 6,
                "num_draws": 0,
                "rating": 2.94119,
                "technical_name": "canis3v3.v0001",
                "thumbnail_url_large": "http://content.faforever.com/faf/vault/map_previews/large/canis3v3.v0001.png",
                "thumbnail_url_small": "http://content.faforever.com/faf/vault/map_previews/small/canis3v3.v0001.png",
                "times_played": 1955,
                "version": "1",
                "author": "Someone"
              },
              "id": 0,
              "type": "map"
            },
            ...
          ]
        }


    """
    where = ''
    args = None
    many = True

    filename_filter = request.values.get('filter[technical_name]')
    if filename_filter:
        where = ' filename = %s'
        args = 'maps/' + filename_filter + '.zip'
        many = False

    results = fetch_data(MapSchema(), TABLE, SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request, where=where, args=args,
                         many=many, enricher=enricher)
    return results


@app.route('/maps/ladder1v1', methods=['GET'])
def laddermaps():
    """
    Lists all maps of the current ladder map pool ( for 1v1)

    **Example Request**:

    .. sourcecode:: http

       GET /maps/ladder1v1

    **Example Response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: text/javascript

        {
          "data": [
            {
              "attributes": {
                "battle_type": "FFA",
                "description": "<LOC canis3v3_Description>",
                "display_name": "canis3v3",
                "download_url": "http://content.faforever.com/faf/vault/maps/canis3v3.v0001.zip",
                "downloads": 5970,
                "id": 0,
                "map_type": "skirmish",
                "max_players": 6,
                "num_draws": 0,
                "rating": 2.94119,
                "technical_name": "canis3v3.v0001",
                "thumbnail_url_large": "http://content.faforever.com/faf/vault/map_previews/large/maps/canis3v3.v0001.zip",
                "thumbnail_url_small": "http://content.faforever.com/faf/vault/map_previews/small/maps/canis3v3.v0001.zip",
                "times_played": 1955,
                "version": "1"
              },
              "id": 0,
              "type": "map"
            },
            ...
          ]
        }


    """
    LADDER_TABLE = "( {} ) JOIN ladder_map ON map.id = ladder_map.idmap".format(TABLE)

    results = fetch_data(MapSchema(), LADDER_TABLE, SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request, enricher= enricher)
    return results


def enricher(map):
    if 'thumbnail_url_small' in map:
        if not map['thumbnail_url_small']:
            del map['thumbnail_url_small']
        else:
            map['thumbnail_url_small'] = '{}/faf/vault/map_previews/small/{}'.format(
                app.config['CONTENT_URL'], urllib.parse.quote(map['thumbnail_url_small']))

    if 'thumbnail_url_large' in map:
        if not map['thumbnail_url_large']:
            del map['thumbnail_url_large']
        else:
            map['thumbnail_url_large'] = '{}/faf/vault/map_previews/large/{}'.format(
                app.config['CONTENT_URL'], urllib.parse.quote(map['thumbnail_url_large']))

    if 'download_url' in map:
        map['download_url'] = '{}/faf/vault/{}'.format(app.config['CONTENT_URL'],
                                                       urllib.parse.quote(map['download_url']))


def file_allowed(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def process_uploaded_map(temp_map_path, is_ranked):
    map_info = parse_map_info(temp_map_path, validate=False)
    validate_map_info(map_info)

    display_name = map_info['display_name']
    version = map_info['version']
    description = map_info['description']
    max_players = map_info['max_players']
    map_type = map_info['type']
    battle_type = map_info['battle_type']

    size = map_info['size']
    width = int(size[0])
    height = int(size[1])

    if len(display_name) > 100:
        raise ApiException([Error(ErrorCode.MAP_NAME_TOO_LONG, 100, len(display_name))])

    user_id = request.oauth.user.id
    if not can_upload_map(display_name, user_id):
        raise ApiException([Error(ErrorCode.MAP_NOT_ORIGINAL_AUTHOR, display_name)])

    if map_exists(display_name, version):
        raise ApiException([Error(ErrorCode.MAP_VERSION_EXISTS, display_name, version)])

    zip_file_path = generate_zip(temp_map_path, str(Path(temp_map_path).parent))
    zip_file_name = os.path.basename(zip_file_path)
    target_map_path = os.path.join(app.config['MAP_UPLOAD_PATH'], zip_file_name)
    if os.path.isfile(target_map_path):
        raise ApiException([Error(ErrorCode.MAP_NAME_CONFLICT, zip_file_name)])

    shutil.move(temp_map_path, target_map_path)

    generate_map_previews(target_map_path, {
        128: os.path.join(app.config['MAP_PREVIEW_PATH'], 'small'),
        512: os.path.join(app.config['MAP_PREVIEW_PATH'], 'large')
    })

    with db.connection:
        cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)

        cursor.execute("""INSERT INTO map (display_name, map_type, battle_type, author)
                        SELECT %(display_name)s, %(map_type)s, %(battle_type)s, %(author)s
                        WHERE NOT EXISTS (
                            SELECT display_name FROM map WHERE display_name = %(display_name)s
                        ) LIMIT 1""",
                       {
                           'display_name': display_name,
                           'map_type': map_type,
                           'battle_type': battle_type,
                           'author': user_id
                       })

        cursor.execute("""INSERT INTO map_version (
                            description, max_players, width, height, version, filename, ranked, map_id
                        )
                        VALUES (
                            %(description)s, %(max_players)s, %(width)s, %(height)s, %(version)s, %(filename)s,
                            %(ranked)s,
                            (SELECT id FROM map WHERE display_name = %(display_name)s)
                        )""",
                       {
                           'description': description,
                           'max_players': max_players,
                           'width': width,
                           'height': height,
                           'version': version,
                           'filename': "maps/" + zip_file_name,
                           'display_name': display_name,
                           'ranked': 1 if is_ranked else 0
                       })


def validate_map_info(map_info):
    errors = []
    if not map_info.get('display_name'):
        errors.append(Error(ErrorCode.MAP_NAME_MISSING))
    if not map_info.get('description'):
        errors.append(Error(ErrorCode.MAP_DESCRIPTION_MISSING))
    if not map_info.get('max_players') \
            or map_info.get('battle_type') != 'FFA':
        errors.append(Error(ErrorCode.MAP_FIRST_TEAM_FFA))
    if not map_info.get('type'):
        errors.append(Error(ErrorCode.MAP_TYPE_MISSING))
    if not map_info.get('size'):
        errors.append(Error(ErrorCode.MAP_SIZE_MISSING))
    if not map_info.get('version'):
        errors.append(Error(ErrorCode.MAP_VERSION_MISSING))

    if errors:
        raise ApiException(errors)


def extract_preview(zip, member, target_folder, target_name):
    with zip.open(member) as source:
        target_path = os.path.join(target_folder, target_name)

        with open(target_path, "wb") as target:
            shutil.copyfileobj(source, target)


def map_exists(display_name, version):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute('''select count(*) from map_version v join map m on m.id = v.map_id
                          where m.display_name = %s and v.version = %s''', (display_name, version))

        return cursor.fetchone()[0] > 0


def can_upload_map(name, user_id):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute('SELECT count(*) FROM map WHERE display_name = %s AND author != %s', (name, user_id))

        return cursor.fetchone()[0] == 0
