import json
import os
from peewee import IntegrityError
from werkzeug.utils import secure_filename
from api import *

from flask import request

@app.route("/avatar", methods=['GET', 'POST'])
def avatars():
    if request.method == 'POST':

        file = request.files['file']
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['AVATAR_FOLDER'], filename))

        try:
            avatar = Avatar.create(url=app.config['AVATAR_URL'], tooltip=request.form['tooltip'])
        except IntegrityError:
            return json.dumps(dict(error="Avatar already exists")), 400

        return avatar.dict()

    else:
        return [avatar.dict() for avatar in Avatar.select()]

@app.route("/avatar/<int:id>", methods=['GET', 'PUT'])
def avatar(id):
    if request.method == 'GET':
        return Avatar.get(Avatar.id == id).dict()
    elif request.method == 'PUT':
        raise NotImplemented('')
