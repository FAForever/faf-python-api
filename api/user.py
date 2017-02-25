from flask_login import UserMixin

from enum import IntEnum

import faf.db as db

class UserGroup(IntEnum):
    NONE = 0,
    MODERATOR = 1,
    ADMIN = 2


class User(UserMixin):
    """
    User model for API. It collects the username, password, and ID.

    .. py:attribute:: id

        The users ID

        :type: str

    .. py:attribute:: username

        The users username

        :type: str

    .. py:attribute:: password

        The users password

        :type: str
    """
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.username = kwargs.get('login')
        self.password = kwargs.get('password')

    @classmethod
    def get_by_id(cls, user_id):
        """
        Find user by id.

        :param str user_id: The user ID used to request a user from
        :returns:
            :class: `User` if user is found, None otherwise
        """
        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            cursor.execute("SELECT id, login FROM login WHERE id = %s", user_id)

            user = cursor.fetchone()
            return User(**user) if user else None

    @classmethod
    def get_by_username(cls, username):
        """
        Find user by username.

        :param str username: The username used to request a user from
        :returns:
            :class: `User` if user is found, None otherwise

        """
        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            # Need to use lowercase comparison until we change the collation in the db and prune dupes
            cursor.execute("SELECT id, login, password FROM login WHERE LOWER(login) = %s", username.lower())

            user = cursor.fetchone()
            return User(**user) if user else None

    @classmethod
    def is_banned(cls, username):
        """
        Checks whether a user is banned.

        :param str username: The username to check
        :returns: (`True`, reason) if the user is currently banned, (`False`, `None`) otherwise

        """
        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            # Need to use lowercase comparison until we change the collation in the db and prune dupes
            cursor.execute("SELECT reason FROM lobby_ban b "
                           "JOIN `login` l ON l.id = b.idUser "
                           "WHERE LOWER(l.login) = %s AND b.expires_at > NOW()", username.lower())

            result = cursor.fetchone()
            reason = result['reason'] if result else None
            return result is not None, reason

    def usergroup(self):
        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            cursor.execute("SELECT `group` from lobby_admin WHERE user_id=%s", self.id)
            result = cursor.fetchone()
            group = UserGroup(result['group']) if result else UserGroup.NONE
            return group

    @classmethod
    def get_usergroup(cls, username):
        """
        Checks whether a user is a mod/admin according to lobby_admin table.

        :param str username: The username to check
        :returns: UserGroup enum

        """
        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            # Need to use lowercase comparison until we change the collation in the db and prune dupes
            cursor.execute("SELECT la.group FROM lobby_admin la "
                           "JOIN `login` l ON l.id = la.user_id "
                           "WHERE LOWER(l.login) = %s", username.lower())

            result = cursor.fetchone()
            group = UserGroup(result['group']) if result else UserGroup.NONE
            return group


