from flask_login import UserMixin

import faf.db as db


class User(UserMixin):
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.username = kwargs.get('login')
        self.password = kwargs.get('password')

    @classmethod
    def get_by_id(cls, user_id):
        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            cursor.execute("SELECT id, login FROM login WHERE id = %s", user_id)

            user = cursor.fetchone()
            return User(**user) if user else None

    @classmethod
    def get_by_username(cls, username):
        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            # Need to use lowercase comparison until we change the collation in the db and prune dupes
            cursor.execute("SELECT id, login, password FROM login WHERE LOWER(login) = %s", username.lower())

            user = cursor.fetchone()
            return User(**user) if user else None
