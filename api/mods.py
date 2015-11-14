import os

from flask import request, url_for
from werkzeug.utils import secure_filename, redirect

import faf.db as db
from api import app, InvalidUsage

ALLOWED_EXTENSIONS = {'zip'}


@app.route('/mods/upload', methods=['POST'])
def mods_upload():
    file = request.files.get('file')
    if not file:
        raise InvalidUsage("No file has been provided")

    if not allowed_file(file.filename):
        raise InvalidUsage("Invalid file extension")

    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['MOD_UPLOAD_PATH'], filename))
    return "ok"


@app.route('/mods')
def get_mods():
    with db.connection.cursor() as cursor:
        cursor.execute('SELECT name from table_mod')
        mods = []
        while cursor.rowcount > 1:
            mods.append(cursor.fetchone())
    return {
        'data': [
            {
                'type': 'mods',
                'id': 1
            }
        ]
    }


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS
