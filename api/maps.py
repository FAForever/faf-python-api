import os

from flask import request
from werkzeug.utils import secure_filename

from api import app, InvalidUsage
from faf import db

ALLOWED_EXTENSIONS = {'zip'}
MAPS_PER_PAGE = 100


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
    order_column = request.values.get('order_column', 'times_played')
    if order_column not in {'name', 'max_players', 'map_type', 'battle_type', 'map_sizeX', 'map_sizeY', 'downloads',
                            'num_draws', 'rating', 'times_played'}:
        raise InvalidUsage("Invalid order column")

    order = request.values.get('order', 'ASC')
    if order.lower() not in {'asc', 'desc'}:
        raise InvalidUsage("Invalid order")

    max_items = int(request.values.get('max', MAPS_PER_PAGE))
    if max_items > MAPS_PER_PAGE:
        raise InvalidUsage("Invalid max")

    page = int(request.values.get('page', 1))
    if page < 1:
        raise InvalidUsage("Invalid page")

    offset = (page - 1) * max_items
    limit = max_items

    with db.connection:
        cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
        cursor.execute("""
            SELECT
                map.mapuid as id,
                map.name,
                map.description,
                COALESCE(map.max_players, 0) as max_players,
                map.map_type,
                map.battle_type,
                COALESCE(map.map_sizeX, 0) as map_size_x,
                COALESCE(map.map_sizeY, 0) as map_size_y,
                map.version,
                map.filename,
                COALESCE(features.downloads, 0) as downloads,
                COALESCE(features.num_draws, 0) as num_draws,
                COALESCE(features.rating, 0) as rating,
                COALESCE(features.times_played, 0) as times_played
            FROM table_map map
            LEFT JOIN table_map_features features
                ON features.map_id = map.id
            ORDER BY {} {}
            LIMIT %(offset)s, %(limit)s
        """.format(order_column, order), dict(offset=offset, limit=limit))

        result = cursor.fetchall()

    data = []

    for row in result:
        data.append({
            'type': 'map',
            'id': row['id'],
            'attributes': {
                'name': row['name'],
                'description': row['description'],
                'max_players': int(row['max_players']),
                'map_type': row['map_type'],
                'battle_type': row['battle_type'],
                'map_size_x': int(row['map_size_x']),
                'map_size_y': int(row['map_size_y']),
                'version': row['version'],
                'filename': row['filename'],
                'downloads': int(row['downloads']),
                'num_draws': int(row['num_draws']),
                'rating': float(row['rating']),
                'times_played': int(row['times_played'])
            }
        })

    return {'data': data}


def file_allowed(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS
