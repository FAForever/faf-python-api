import os

from flask import request, url_for
from werkzeug.utils import secure_filename, redirect

import faf.db as db
from api import app, InvalidUsage

ALLOWED_EXTENSIONS = {'zip'}


@app.route('/maps/upload', methods=['POST'])
def maps_upload():
    file = request.files.get('file')
    if not file:
        raise InvalidUsage("No file has been provided")

    if not allowed_file(file.filename):
        raise InvalidUsage("Invalid file extension")

    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['MAP_UPLOAD_PATH'], filename))
    return "ok"


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS
