import json
import os
from peewee import IntegrityError
from werkzeug.utils import secure_filename
from api import *

from flask import request

@app.route("/avatar", methods=['GET', 'POST'])
def avatars():
    """
    Displays avatars

    .. warning:: Not working currently. Broken.

    **Example Request**:

    .. sourcecode:: http

       GET, POST /avatar

    **Example Response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: text/javascript


    :param file: The avatar being added to the system
    :type file: file
    :status 200: No error

    .. todo:: Probably would be better to isolate methods GET and POST methods...
    """
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
    """
    Displays individual avatars

    .. warning:: Not working currently. Broken.

    **Example Request**:

    .. sourcecode:: http

       GET, PUT /avatar/781

    **Example Response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: text/javascript


    :param id: The avatar being added to the system
    :type id: int
    :status 200: No error

    .. todo:: Probably would be better to isolate methods GET and PUT methods...
    """
    if request.method == 'GET':
        return Avatar.get(Avatar.id == id).dict()
    elif request.method == 'PUT':
        raise NotImplemented('')
