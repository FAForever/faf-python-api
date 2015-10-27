from flask_login import UserMixin

import faf.db as db


class User(UserMixin):
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.username = kwargs.get('username')
        self.password = kwargs.get('password')

    @classmethod
    def get_by_id(cls, user_id):
        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            cursor.execute("SELECT id, username FROM auth_user WHERE id = %s", user_id)

            user = cursor.fetchone()
            return User(**user) if user else None

    @classmethod
    def get_by_username(cls, username):
        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            cursor.execute("SELECT id, username, password FROM auth_user WHERE username = %s", username)

            user = cursor.fetchone()
            return User(**user) if user else None
