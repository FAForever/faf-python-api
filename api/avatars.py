import os
from werkzeug.utils import secure_filename
from api import *

import faf.db as db
from api.error import ApiException, Error, ErrorCode

from flask import request, jsonify

import pymysql

import logging
logger = logging.getLogger(__name__)

class Avatar:
    """
    Avatar model/db class

    The implementation of this class is a little tricky since we have to handle
    the url and filename.

    It also does not ensure 100% consistency. E.g. it allows for avatars to be
    inserted without uploading the corresponding avatar file.
    """

    def __init__(self, id=None, filename=None, url=None, tooltip=None, **kwargs):
        """
        Constructor

        :param int id: database id
        :param string filename: filename / url / whatever
        :param string tooltip: tooltip
        """
        self.URLBASE = app.config.get('AVATAR_URL', 'http://content.faforever.com/faf/avatars/')
        self.FILEBASE = app.config.get('AVATAR_FOLDER', '/content/faf/avatars/')

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
        if isinstance(user, User):
            user = user.id

        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            cursor.execute('select al.*, a.selected as selected, a.expires_at as assignment_expires_at, a.create_time as assignment_create_time, a.update_time as assignment_update_time from avatars_list as al JOIN avatars as a on (al.id = a.idAvatar) where a.idUser = %s', user)
            avatars = cursor.fetchall()
            return avatars

    @classmethod
    def remove_user_avatars(cls, user, avatars):
        """
        Remove avatars from user
        """

        if isinstance(user, User):
            user_id = user.id
        else:
            user_id = int(user)

        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            #FIXME: make "where idAvatar in (set)" query?
            for avatar in avatars:
                if isinstance(avatar, cls):
                    avatar_id = avatar.id
                else:
                    avatar_id = int(avatar)
                cursor.execute('delete from avatars where idUser=%s and idAvatar=%s', [user_id, avatar_id])

    @classmethod
    def add_user_avatars(cls, user, avatars, expires_in=None):
        """
        Add avatars to user
        """

        if isinstance(user, User):
            user_id = user.id
        else:
            user_id = int(user)

        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            #FIXME: make "where idAvatar in (set)" query?
            for avatar in avatars:
                if isinstance(avatar, cls):
                    avatar_id = avatar.id
                else:
                    avatar_id = int(avatar)
                if expires_in is not None:
                    cursor.execute('insert into avatars (idUser, idAvatar, expires_at) values (%s, %s, DATE_ADD(NOW(), INTERVAL %s DAY))', [user_id, avatar_id, expires_in])
                else:
                    cursor.execute('insert into avatars (idUser, idAvatar) values (%s, %s)', [user_id, avatar_id])

    def get_avatar_users(self, attrs = ['id', 'login']):
        """
        Get all users that have this avatar

        Returns None if avatar instance does not have an id, otherwise list of user id's
        """
        if self.id is not None:
            with db.connection:
                cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
                cursor.execute('SELECT l.* from login as l join avatars as a on (a.idUser = l.id) WHERE idAvatar = %s', self.id)

                return [{key: rec[key] for key in attrs} for rec in cursor.fetchall()]
        else:
            return None

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
            raise ApiException([Error(ErrorCode.AVATAR_FILE_EXISTS)])
        with open(dest, 'wb') as fh:
            fh.write(avatar_file.read())

    def delete_file(self):
        """
        Deletes avatar file
        """
        os.unlink(self._path())



    def delete(self):
        """
        Deletes avatar

        WARNING: Does not check if avatar is still in use!
        """
        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            cursor.execute("DELETE FROM avatars_list WHERE id=%s", self.id)

@app.route("/user_avatars", methods=['GET', 'POST', 'DELETE'])
def user_avatars():
    if request.method != 'GET':
        valid, req = oauth.verify_request([])
        if not valid:
            raise ApiException([Error(ErrorCode.AUTHENTICATION_NEEDED)])
        else:
            current_user = User.get_by_id(req.user.id)
            print("user:", current_user.id, current_user.username)
            print("checking usergroup:", current_user.usergroup())
            if not current_user.usergroup() >= UserGroup.MODERATOR:
                raise ApiException([Error(ErrorCode.FORBIDDEN)])

    if request.method == 'POST':
        user_id = request.form.get('user_id', type=int)
        expires_in = request.form.get('expires_in', type=int)
        avatar_ids = request.form.getlist('avatar_id', type=int)
        Avatar.add_user_avatars(user_id, avatar_ids, expires_in)
        return 'ok'
    elif request.method == 'DELETE':
        user_id = request.form.get('user_id', type=int)
        if user_id is not None:
            avatar_ids = request.form.getlist('avatar_id', type=int)
            Avatar.remove_user_avatars(user_id, avatar_ids)
            return jsonify(dict(status='Removed avatar from user')), 204
        else:
            raise ApiException([Error(ErrorCode.PARAMETER_MISSING, 'id')])
    elif request.method == 'GET':
        user_id = request.args.get('id', type=int)
        if user_id is not None:
            avatars = Avatar.get_user_avatars(user_id)
            return jsonify(avatars)
        else:
            raise ApiException([Error(ErrorCode.PARAMETER_MISSING, 'id')])


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
            raise ApiException([Error(ErrorCode.AUTHENTICATION_NEEDED)])
        else:
            current_user = User.get_by_id(req.user.id)
            if not current_user.usergroup() >= UserGroup.MODERATOR:
                raise ApiException([Error(ErrorCode.FORBIDDEN)])

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
            raise ApiException([Error(ErrorCode.AVATAR_NOT_FOUND)])
    elif request.method == 'PUT':
        avatar_file = request.files['file']
        avatar_filename = secure_filename(avatar_file.filename)
        avatar_tooltip = request.form['tooltip']

        avatar = Avatar(filename=avatar_filename, tooltip=avatar_tooltip)
        avatar.upload(avatar_file)
        try:
            avatar.insert()
        except pymysql.err.IntegrityError as e:
            try:
                avatar.delete_file()
            except:
                pass
            raise ApiException([Error(ErrorCode.AVATAR_INTEGRITY_ERROR, e.args)])

        return avatar.dict()
    elif request.method == 'DELETE':
        avatar_id = request.form.get('id')
        if id is not None:
            avatar = Avatar.get_by_id(avatar_id)
            if avatar is not None:
                try:
                    avatar.delete()
                    try:
                        avatar.delete_file()
                    except:
                        return jsonify(dict(status='Deleted avatar', detail='Couldn\'t delete the file though')), 204
                    return jsonify(dict(status='Deleted avatar')), 204
                except pymysql.err.IntegrityError:
                    raise ApiException([Error(ErrorCode.AVATAR_IN_USE)])
            else:
                raise ApiException([Error(ErrorCode.AVATAR_NOT_FOUND)])
        else:
            raise ApiException([Error(ErrorCode.AVATAR_ID_MISSING)])
    elif request.method == 'GET':
        avatar_id = request.args.get('id')
        if avatar_id is not None:
            avatar = Avatar.get_by_id(avatar_id)
            if avatar is not None:
                return avatar.dict()
            else:
                raise ApiException([Error(ErrorCode.AVATAR_NOT_FOUND)])
        else:
            return jsonify(Avatar.get_all())


@app.route("/avatar/<int:id>", methods=['GET'])
def avatar(id):
    """
    Displays individual avatars

    **Example Request**:

    .. sourcecode:: http

       GET /avatar/781

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
            raise ApiException([Error(ErrorCode.AVATAR_NOT_FOUND)])

@app.route("/avatar/<int:id>/users", methods=['GET'])
def avatar_users(id):
    if request.method == 'GET':
        avatar = Avatar.get_by_id(id)
        attrs = request.args.getlist('attr')
        if len(attrs) < 1:
            attrs = ['id', 'login']
        if avatar is not None:
            return jsonify(avatar.get_avatar_users(attrs))
        else:
            return jsonify(dict(error='Not found')), 404

