import os

from flask import request
from werkzeug.utils import secure_filename

import faf.db as db
from api import app, InvalidUsage

ALLOWED_EXTENSIONS = {'zip'}
MODS_PER_PAGE = 100


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


@app.route("/mods/names")
def mods_names():

    with db.connection:
        cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
        cursor.execute("SELECT name FROM table_mod ORDER BY name ASC")

        result = cursor.fetchall()

    data = []

    for row in result:
        data.append(row['name'])

    return {'data': data}


@app.route('/mods')
def mods():
    order_column = request.values.get('order_column', 'likes')
    if order_column not in {'likes', 'plays', 'create_time'}:
        raise InvalidUsage("Invalid order column")

    order = request.values.get('order', 'ASC')
    if order.lower() not in {'asc', 'desc'}:
        raise InvalidUsage("Invalid order")

    max_items = int(request.values.get('max', MODS_PER_PAGE))
    if max_items > MODS_PER_PAGE:
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
                uid as id,
                name,
                description,
                version,
                author,
                ui as is_ui,
                UNIX_TIMESTAMP(date) as create_time,
                downloads,
                likes,
                played as plays,
                filename,
                icon as icon_filename,
                ranked as is_ranked
            FROM table_mod
            ORDER BY {} {}
            LIMIT %(offset)s, %(limit)s
        """.format(order_column, order), dict(offset=offset, limit=limit))

        result = cursor.fetchall()

    data = []

    for row in result:
        data.append({
            'type': 'mod',
            'id': row['id'],
            'attributes': {
                'name': row['name'],
                'description': row['description'],
                'version': row['version'],
                'author': row['author'],
                'downloads': row['downloads'],
                'likes': row['likes'],
                'plays': row['plays'],
                'filename': row['filename'],
                'icon_filename': row['icon_filename'],
                'is_ui': bool(row['is_ui']),
                'is_ranked': bool(row['is_ranked']),
                'create_time': row['create_time']
            }
        })

    return {'data': data}


def file_allowed(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS
