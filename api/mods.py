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
    result = fetch_data(ModSchema(), 'table_mod', SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request,
                        where="WHERE uid = %s", args=mod_uid, many=False)

    if 'id' not in result['data']:
        return {'errors': [{'title': 'No mod with this uid was found'}]}, 404

    return result


@app.route('/mods')
def mods():
    results = fetch_data(ModSchema(), 'table_mod', SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request)
    for mod in results['data']:
        enrich_mod(mod['attributes'])
    return results


def enrich_mod(mod):
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
