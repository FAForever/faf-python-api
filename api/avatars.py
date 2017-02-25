import json
import os
from peewee import IntegrityError
from werkzeug.utils import secure_filename
from api import *
from urllib.parse import urlparse

import faf.db as db

from flask import request

import logging
logger = logging.getLogger(__name__)

class Avatar:
    """
    Avatar model/db class

    The implementation of this class is a little tricky since we have to handle
    the url and filename.
    """

    URLBASE = app.config.get('AVATAR_URL', 'http://content.faforever.com/faf/avatars/')
    FILEBASE = app.config.get('AVATAR_FOLDER', '/content/faf/avatars/')

    def __init__(self, id=None, filename=None, url=None, tooltip=None, **kwargs):
        """
        Constructor

        :param int id: database id
        :param string filename: filename / url / whatever
        :param string tooltip: tooltip
        """
        self.id = id
        # FIXME: Dirty hack, done dirt cheap
        filename = filename or url
        if '/' in filename:
            filename = filename.split('/')[-1]
        self.filename = filename
        self.tooltip = tooltip

    def dict(self):
        return {
                'id': self.id,
                'url': self._url(),
                'tooltip': self.tooltip
        }

    def _url(self):
        if self.filename is not None:
            return self.URLBASE + self.filename
        else:
            return None

    def _path(self):
        if self.filename is not None:
            return self.FILEBASE + self.filename
        else:
            return None

    @classmethod
    def get_by_id(cls, avatar_id):
        """
        Find avatar by id.

        :param str avatar_id: The avatar database id
        :returns:
            :class: `Avatar` if avatar is found, None otherwise
        """
        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            cursor.execute("SELECT id, url, tooltip FROM avatars_list WHERE id = %s", avatar_id)

            avatar = cursor.fetchone()
            if avatar is not None:
                return Avatar(**avatar)
            else:
                return None

    @classmethod
    def get_all(cls):
        """
        Get all avatars from db - as dict, because you probably don't need instances.
        """
        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM avatars_list")

            return cursor.fetchall()

    @classmethod
    def get_user_avatars(cls, user):
        """
        Find a user's avatars

        pass user id or User instance

        Get back list of avatars
        """
        if user is User:
            user = user.id

        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            cursor.execute('select al.* from avatars_list as al JOIN avatars as a on (al.id = a.idUser) where a.idUser = %s', user)
            avatars = cursor.fetchall()
            return [Avatar(**record) for record in avatars]

    @classmethod
    def remove_user_avatars(cls, user, avatars):
        """
        Remove avatars from user
        """

        if user is User:
            user_id = user.id
        else:
            user_id = int(user)

        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            #FIXME: make "where idAvatar in (set)" query?
            for avatar in avatars:
                if avatar is Avatar:
                    avatar_id = avatar.id
                else:
                    avatar_id = int(avatar)
                cursor.execute('delete from avatars where idUser=%s and idAvatar=%s', [user_id, avatar_id])

    def add_user_avatars(cls, user, avatars):
        """
        Add avatars to user
        """

        if user is User:
            user_id = user.id
        else:
            user_id = int(user)

        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            #FIXME: make "where idAvatar in (set)" query?
            for avatar in avatars:
                if avatar is Avatar:
                    avatar_id = avatar.id
                else:
                    avatar_id = int(avatar)
                cursor.execute('insert into avatars (idUser, idAvatar) values (%s, %s)', [user_id, avatar_id])

    def insert(self):
        """
        Inserts avatar into db
        """

        # if an avatar has an id, it must already be in the database.
        if self.id is not None:
            raise Exception('Avatar already has an id - refusing to insert.')
        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            cursor.execute("INSERT INTO avatars_list (url, tooltip) VALUES (%s, %s)", [self._url(), self.tooltip])
            self.id = cursor.lastrowid

    def update(self):
        """
        Updates avatar tooltip
        """
        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            cursor.execute("UPDATE avatars_list SET tooltip=%s WHERE id=%s", [self.tooltip, self.id])


    def upload(self, avatar_file, overwrite=False):
        """
        Copies avatar file to filesystem

        :param avatar_file flo: file-like object of the avatar file
        :param overwrite bool: Only overwrites existing file if true
        """
        dest = self._path()
        if os.path.exists(dest) and not overwrite:
            raise Exception('Avatar file exists!')
        with open(dest, 'wb') as fh:
            fh.write(avatar_file.read())

    def delete(self):
        """
        Deletes avatar

        WARNING: Does not check if avatar is still in use!
        """
        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            cursor.execute("DELETE FROM avatars_list WHERE id=%s", self.id)



@app.route("/avatar", methods=['GET', 'POST', 'PUT', 'DELETE'])
def avatars():
    """
    Displays avatars

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
    if request.method != 'GET':
        valid, req = oauth.verify_request([])
        if not valid:
            return json.dumps('You are not authenticated.'), 401
        else:
            current_user = User.get_by_id(req.user.id)
            if not current_user.usergroup() >= UserGroup.MODERATOR:
                return json.dumps('You are not authorized to do this.'), 401

    if request.method == 'POST':
        logger.debug('Handling POST')
        avatar_id = request.form.get('id')
        avatar_tooltip = request.form.get('tooltip')
        avatar_file = request.files.get('file')
        logger.debug('Fetched params: id={} tooltip={} file={}'.format(repr(avatar_id), repr(avatar_tooltip), repr(avatar_file)))

        avatar = Avatar.get_by_id(avatar_id)

        if avatar is not None:
            if avatar_tooltip != avatar.tooltip:
                avatar.tooltip = avatar_tooltip
                avatar.update()
            if avatar_file is not None:
                avatar.upload(avatar_file, overwrite=True)
            return avatar.dict()
        else:
            return json.dumps(dict(error="Avatar not found")), 404
    elif request.method == 'PUT':
        avatar_file = request.files['file']
        avatar_filename = secure_filename(avatar_file.filename)
        avatar_tooltip = request.form['tooltip']

        avatar = Avatar(filename=avatar_filename, tooltip=avatar_tooltip)
        try:
            avatar.upload(avatar_file)
        except Exception as e:
            return json.dumps(dict(error=e.args)), 400

        avatar.insert()

        return avatar.dict()
    elif request.method == 'DELETE':
        avatar_id = request.form.get('id')
        if id is not None:
            avatar = Avatar.get_by_id(avatar_id)
            if avatar is not None:
                avatar.delete()
                return json.dumps(dict(status='Deleted avatar')), 204
            else:
                return json.dumps(dict(error='Not found')), 404
        else:
            return json.dumps(dict(error='id parameter missing')), 400
    elif request.method == 'GET':
        avatar_id = request.args.get('id')
        if avatar_id is not None:
            avatar = Avatar.get_by_id(avatar_id)
            if avatar is not None:
                return avatar.dict()
            else:
                return json.dumps(dict(error='Not found')), 404
        else:
            return json.dumps(Avatar.get_all())


@app.route("/avatar/<int:id>", methods=['GET'])
def avatar(id):
    """
    Displays individual avatars

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
        avatar = Avatar.get_by_id(id)
        if avatar is not None:
            return avatar.dict()
        else:
            return json.dumps(dict(error='Not found')), 404
