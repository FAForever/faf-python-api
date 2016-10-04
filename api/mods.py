import json
import os
import shutil
import tempfile
import urllib.parse
from zipfile import ZipFile

from faf.api import ModSchema
from faf.tools.fa.mods import parse_mod_info, generate_thumbnail_file_name, generate_zip_file_name
from flask import request
from werkzeug.utils import secure_filename

from api import app, oauth
from api.error import ApiException, ErrorCode
from api.error import Error
from api.query_commons import fetch_data
from faf import db

ALLOWED_EXTENSIONS = ['zip']
MAX_PAGE_SIZE = 1000

SELECT_EXPRESSIONS = {
    'id': 'v.uid',
    'display_name': 'm.display_name',
    'description': 'v.description',
    'version': 'v.version',
    'author': 'm.author',
    'type': 'v.type',
    'create_time': 'v.create_time',
    'downloads': 's.downloads',
    'likes': 's.likes',
    'times_played': 's.times_played',
    'is_ranked': 'v.ranked',
    # download_url will be URL encoded and made absolute in enrich_mod
    'download_url': 'v.filename',
    # thumbnail_url will be URL encoded and made absolute in enrich_mod
    'thumbnail_url': 'v.icon'
}

MODS_TABLE = '`mod` m JOIN mod_version v ON m.id = v.mod_id JOIN mod_stats s ON m.id = s.mod_id'


@app.route('/mods/upload', methods=['POST'])
@oauth.require_oauth('upload_mod')
def mods_upload():
    """
    Uploads a new mod into the system.

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
    metadata_string = request.form.get('metadata')

    if not file:
        raise ApiException([Error(ErrorCode.UPLOAD_FILE_MISSING)])

    if not metadata_string:
        raise ApiException([Error(ErrorCode.UPLOAD_METADATA_MISSING)])

    if not file_allowed(file.filename):
        raise ApiException([Error(ErrorCode.UPLOAD_INVALID_FILE_EXTENSION, *ALLOWED_EXTENSIONS)])

    metadata = json.loads(metadata_string)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_mod_path = os.path.join(temp_dir, secure_filename(file.filename))
        file.save(temp_mod_path)
        process_uploaded_mod(temp_mod_path, metadata.get('is_ranked', False))

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
    result = fetch_data(ModSchema(), MODS_TABLE, SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request,
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
    return fetch_data(ModSchema(), MODS_TABLE, SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request, enricher=enricher,
                      where='v.hidden = 0')


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


def process_uploaded_mod(temp_mod_path, is_ranked):
    mod_info = parse_mod_info(temp_mod_path)
    validate_mod_info(mod_info)

    display_name = mod_info['name']
    uid = mod_info['uid']
    version = mod_info['version']
    description = mod_info['description']
    author = mod_info['author']
    mod_type = 'UI' if mod_info['ui_only'] else 'SIM'

    user_id = request.oauth.user.id
    if not can_upload_mod(display_name, user_id):
        raise ApiException([Error(ErrorCode.MOD_NOT_ORIGINAL_AUTHOR, display_name)])

    if mod_exists(display_name, version):
        raise ApiException([Error(ErrorCode.MOD_VERSION_EXISTS, display_name, version)])

    zip_file_name = generate_zip_file_name(display_name, version)
    target_mod_path = os.path.join(app.config['MOD_UPLOAD_PATH'], zip_file_name)
    if os.path.isfile(target_mod_path):
        raise ApiException([Error(ErrorCode.MOD_NAME_CONFLICT, zip_file_name)])

    thumbnail_path = extract_thumbnail(temp_mod_path, mod_info)
    shutil.move(temp_mod_path, target_mod_path)

    with db.connection:
        cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)

        cursor.execute("""INSERT INTO `mod` (display_name, author, uploader)
                        SELECT %(display_name)s, %(author)s, %(uploader)s
                        WHERE NOT EXISTS (
                            SELECT display_name FROM `mod`WHERE display_name = %(display_name)s
                        ) LIMIT 1""",
                       {
                           'display_name': display_name,
                           'author': author,
                           'uploader': user_id
                       })

        cursor.execute("""INSERT INTO mod_version (
                            uid, type, description, version, filename, icon, ranked, mod_id
                        )
                        VALUES (
                            %(uid)s, %(type)s, %(description)s, %(version)s, %(filename)s, %(icon)s, %(ranked)s,
                            (SELECT id FROM `mod`WHERE display_name = %(display_name)s)
                        )""",
                       {
                           'uid': uid,
                           'type': mod_type,
                           'description': description,
                           'version': version,
                           'filename': 'mods/' + zip_file_name,
                           'icon': os.path.basename(thumbnail_path) if thumbnail_path else None,
                           'ranked': 1 if is_ranked else 0,
                           'display_name': display_name,
                       })


def validate_mod_info(mod_info):
    errors = []
    name = mod_info.get('name')
    if not name:
        errors.append(Error(ErrorCode.MOD_NAME_MISSING))
    if len(name) > 100:
        raise ApiException([Error(ErrorCode.MOD_NAME_TOO_LONG, 100, len(name))])
    if not mod_info.get('uid'):
        errors.append(Error(ErrorCode.MOD_UID_MISSING))
    if not mod_info.get('version'):
        errors.append(Error(ErrorCode.MOD_VERSION_MISSING))
    if not mod_info.get('description'):
        errors.append(Error(ErrorCode.MOD_DESCRIPTION_MISSING))
    if not mod_info.get('author'):
        errors.append(Error(ErrorCode.MOD_DESCRIPTION_MISSING))
    if 'ui_only' not in mod_info:
        errors.append(Error(ErrorCode.MOD_UI_ONLY_MISSING))

    if errors:
        raise ApiException(errors)


def extract_thumbnail(zip_file, mod_info):
    if 'icon' not in mod_info:
        return

    with ZipFile(zip_file) as zip:
        for member in zip.namelist():
            if member.endswith(mod_info['icon']):
                thumbnail_file_name = generate_thumbnail_file_name(mod_info['name'], mod_info['version'])
                target_path = os.path.join(app.config['MOD_THUMBNAIL_PATH'], thumbnail_file_name)
                with zip.open(member) as source, open(target_path, "wb") as target:
                    shutil.copyfileobj(source, target)

                return target_path


def mod_exists(display_name, version):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute('''select count(*) from mod_version v join `mod` m on m.id = v.mod_id
                          where m.display_name = %s and v.version = %s''', (display_name, version))

        return cursor.fetchone()[0] > 0


def can_upload_mod(name, user_id):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute('SELECT count(*) FROM `mod` WHERE display_name = %s AND uploader != %s', (name, user_id))

        return cursor.fetchone()[0] == 0
