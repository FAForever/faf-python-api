import os

from flask import request
from pymysql.cursors import DictCursor
from werkzeug.utils import secure_filename

import faf.db as db
from api import app, InvalidUsage
from faf.api import ModSchema

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


@app.route('/mods/<mod_uid>')
def mod(mod_uid):
    with db.connection:
        cursor = db.connection.cursor(DictCursor)
        cursor.execute("""
            SELECT id,
                uid,
                name,
                description,
                version,
                author,
                ui as is_ui,
                date as create_time,
                downloads,
                likes,
                played as plays,
                filename,
                icon as icon_filename,
                ranked as is_ranked
            FROM table_mod
            WHERE uid=%(mod_uid)s""", dict(mod_uid=mod_uid))
        result = cursor.fetchone()
        if not result:
            return {'errors': [{'title': 'No mod with this uid was found'}]}, 404
        schema = ModSchema()
        serialized, errors = schema.dump(result)
        if not errors:
            return serialized
        return {'errors': [
            {'title': 'Integrity Error',
             'detail': 'Database returned garbage'},
            *errors
        ]}, 500  # pragma: no cover


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
        cursor = db.connection.cursor(DictCursor)
        cursor.execute("""
            SELECT
                uid as id,
                name,
                description,
                version,
                author,
                ui as is_ui,
                date as create_time,
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

    schema = ModSchema()
    result, errors = schema.dump(result, many=True)
    print(result)
    if errors:
        return {'errors': [
            {'title': 'Integrity Error',
             'detail': 'Database returned garbage'},
            *errors
        ]}, 500  # pragma: no cover
    return result


def file_allowed(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS
