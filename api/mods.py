import os

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
    'filename': 'filename',
    'icon_filename': 'icon',
    'is_ranked': 'ranked',
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
    return fetch_data(ModSchema(), 'table_mod', SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request)


def file_allowed(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS
