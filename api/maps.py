import os

from faf.api.map_schema import MapSchema
from flask import request
from werkzeug.utils import secure_filename

from api import app, InvalidUsage
from api.query_commons import fetch_data

ALLOWED_EXTENSIONS = {'zip'}
MAX_PAGE_SIZE = 1000

SELECT_EXPRESSIONS = {
    'id': 'map.mapuid',
    'name': 'map.name',
    'description': 'map.description',
    'max_players': 'COALESCE(map.max_players, 0)',
    'map_type': 'map.map_type',
    'battle_type': 'map.battle_type',
    'map_sizeX': 'COALESCE(map.map_sizeX, 0)',
    'map_sizeY': 'COALESCE(map.map_sizeY, 0)',
    'version': 'map.version',
    'filename': 'map.filename',
    'downloads': 'COALESCE(features.downloads, 0)',
    'num_draws': 'COALESCE(features.num_draws, 0)',
    'rating': 'features.rating',
    'times_played': 'COALESCE(features.times_played, 0)'
}


@app.route('/maps/upload', methods=['POST'])
def maps_upload():
    file = request.files.get('file')
    if not file:
        raise InvalidUsage("No file has been provided")

    if not file_allowed(file.filename):
        raise InvalidUsage("Invalid file extension")

    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['MAP_UPLOAD_PATH'], filename))
    return "ok"


@app.route('/maps')
def maps():
    table = "table_map map LEFT JOIN table_map_features features ON features.map_id = map.id"
    return fetch_data(MapSchema(), table, SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request)


def file_allowed(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS
