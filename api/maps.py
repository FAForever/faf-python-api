import json
import os
import shutil
import tempfile
import urllib.parse
import zipfile

from faf.api.map_schema import MapSchema
from flask import request
from werkzeug.utils import secure_filename
from api import app, InvalidUsage, oauth
from api.query_commons import fetch_data
from api.lua import luaparser

import logging

from faf import db

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'zip'}
MAX_PAGE_SIZE = 1000

SELECT_EXPRESSIONS = {
    'id': 'map.id',
    'display_name': 'map.display_name',
    'description': 'version.description',
    'max_players': 'version.max_players',
    'map_type': 'map.map_type',
    'battle_type': 'map.battle_type',
    'size_x': 'version.size_x',
    'size_y': 'version.size_y',
    'version': 'version.version',
    # download_url will be URL encoded and made absolute in enrich_mod
    'download_url': "version.filename",
    # thumbnail_url_small will be URL encoded and made absolute in enrich_mod
    'thumbnail_url_small': 'version.filename',
    # thumbnail_url_large will be URL encoded and made absolute in enrich_mod
    'thumbnail_url_large': 'version.filename',
    'technical_name': "SUBSTRING(version.filename, LOCATE('/', version.filename)+1, LOCATE('.zip', version.filename)-6)",
    'downloads': 'COALESCE(features.downloads, 0)',
    'num_draws': 'COALESCE(features.num_draws, 0)',
    'rating': 'features.rating',
    'times_played': 'COALESCE(features.times_played, 0)'
}

TABLE = 'map ' \
        'LEFT JOIN table_map_features features ON features.map_id = map.id ' \
        'JOIN map_version version ON version.map_id = map.id'


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
        raise InvalidUsage("No file has been provided")

    if not metadata_string:
        raise InvalidUsage("Value 'metadata' is missing")

    if not file_allowed(file.filename):
        raise InvalidUsage("Invalid file extension")

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
                "version": "1"
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


def enricher(map):
    if 'thumbnail_url_small' in map:
        if not map['thumbnail_url_small']:
            del map['thumbnail_url_small']
        else:
            # FIXME replace .zip with .png
            map['thumbnail_url_small'] = '{}/faf/vault/map_previews/small/{}'.format(app.config['CONTENT_URL'],
                                                                                     map['thumbnail_url_small'])
    if 'thumbnail_url_large' in map:
        if not map['thumbnail_url_large']:
            del map['thumbnail_url_large']
        else:
            # FIXME replace .zip with .png
            map['thumbnail_url_large'] = '{}/faf/vault/map_previews/large/{}'.format(app.config['CONTENT_URL'],
                                                                                     map['thumbnail_url_large'])

    if 'download_url' in map:
        map['download_url'] = '{}/faf/vault/{}'.format(app.config['CONTENT_URL'],
                                                       urllib.parse.quote(map['download_url']))


def file_allowed(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def read_scenario_info(zip, member):
    with tempfile.TemporaryDirectory() as temp_dir:
        scenario_file_path = zip.extract(member, temp_dir)

        scenariolua = luaparser.luaParser(scenario_file_path)
        scenario_infos = scenariolua.parse(
            {'scenarioinfo>name': 'name',
             'size': 'map_size',
             'description': 'description',
             'count:armies': 'max_players',
             'map_version': 'version',
             'type': 'map_type',
             'teams>0>name': 'battle_type'
             }, {'version': '1'})

        if scenariolua.error:
            raise InvalidUsage("Invalid map: " + scenariolua.errorMsg)

        return scenario_infos


def process_uploaded_map(temp_map_path, is_ranked):
    if not zipfile.is_zipfile(temp_map_path):
        raise InvalidUsage("Invalid ZIP file")

    zip = zipfile.ZipFile(temp_map_path, "r", zipfile.ZIP_DEFLATED)

    if zip.testzip() is not None:
        raise InvalidUsage("Invalid ZIP file")

    scenario_info = None
    for member in zip.namelist():
        filename = os.path.basename(member)
        if not filename:
            continue

        # TODO Generate previews instead of expecting them from client
        if filename.endswith(".small.png"):
            extract_preview(zip, member, app.config['SMALL_PREVIEW_UPLOAD_PATH'],
                            filename.replace(".small.png", ".png"))

        elif filename.endswith(".large.png"):
            extract_preview(zip, member, app.config['LARGE_PREVIEW_UPLOAD_PATH'],
                            filename.replace(".large.png", ".png"))

        elif filename.endswith("_scenario.lua"):
            scenario_info = read_scenario_info(zip, member)
            validate_scenario_info(scenario_info)

    if scenario_info is None:
        raise InvalidUsage('Scenario file is missing')

    display_name = scenario_info["name"].strip()
    version = int(scenario_info["version"].strip())
    description = scenario_info["description"].strip()
    max_players = scenario_info["max_players"]
    map_type = scenario_info["map_type"].strip()
    battle_type = scenario_info["battle_type"].strip()

    size = scenario_info["map_size"]
    size_x = int(size["0"])
    size_y = int(size["1"])

    map_file_name = os.path.basename(temp_map_path)
    user_id = request.oauth.user.id
    if not can_upload_map(display_name, map_file_name, user_id):
        raise InvalidUsage('Only the original uploader is allowed to upload this map')

    if map_exists(display_name, version, map_file_name):
        raise InvalidUsage('Map "{}" with version "{}" already exists'.format(display_name, version))

    shutil.move(temp_map_path, os.path.join(app.config['MAP_UPLOAD_PATH'], secure_filename(map_file_name)))

    with db.connection:
        cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)

        cursor.execute("""INSERT INTO map (display_name, map_type, battle_type, ranked, uploader)
                        SELECT %(display_name)s, %(map_type)s, %(battle_type)s, %(ranked)s, %(uploader)s
                        WHERE NOT EXISTS (
                            SELECT display_name FROM map WHERE display_name = %(display_name)s
                        ) LIMIT 1""",
                       {
                           'display_name': display_name,
                           'map_type': map_type,
                           'battle_type': battle_type,
                           'ranked': 1 if is_ranked else 0,
                           'uploader': user_id
                       })

        cursor.execute("""INSERT INTO map_version (
                            description, max_players, size_x, size_y, version, filename, map_id
                        )
                        VALUES (
                            %(description)s, %(max_players)s, %(size_x)s, %(size_y)s, %(version)s, %(filename)s,
                            (SELECT id FROM map WHERE display_name = %(display_name)s)
                        )""",
                       {
                           'description': description,
                           'max_players': max_players,
                           'size_x': size_x,
                           'size_y': size_y,
                           'version': version,
                           'filename': "maps/" + map_file_name,
                           'display_name': display_name
                       })


def validate_scenario_info(scenario_info):
    if 'name' not in scenario_info:
        raise InvalidUsage('Map name has to be specified')
    if 'description' not in scenario_info:
        raise InvalidUsage('Map description has to be specified')
    if 'max_players' not in scenario_info \
            or 'battle_type' not in scenario_info \
            or scenario_info['battle_type'] != 'FFA':
        raise InvalidUsage('Name of first team has to be "FFA"')
    if 'map_type' not in scenario_info:
        raise InvalidUsage('Map type has to be specified')
    if 'map_size' not in scenario_info:
        raise InvalidUsage('Map size has to be specified')
    if 'version' not in scenario_info:
        raise InvalidUsage('Map version has to be specified')


def extract_preview(zip, member, target_folder, target_name):
    filename = os.path.basename(member)
    with zip.open(member) as source:
        target_path = os.path.join(target_folder, target_name)

        with open(target_path, "wb") as target:
            shutil.copyfileobj(source, target)


def map_exists(name, version, map_file_name):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute('SELECT count(*) from map_version WHERE version = %s AND filename LIKE %s',
                       (version, "%" + map_file_name + "%"))

        return cursor.fetchone()[0] > 0


def can_upload_map(name, map_file_name, user_id):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute('SELECT count(*) FROM map WHERE display_name = %s AND uploader != %s', (name, user_id))

        return cursor.fetchone()[0] == 0
