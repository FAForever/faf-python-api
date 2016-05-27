import faf.db as db


class JwtUser(object):
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.username = kwargs.get('username')
        self.public_key = kwargs.get('public_key')

    @classmethod
    def get(cls, username):
        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            cursor.execute("""
            SELECT
                id,
                username,
                public_key
            FROM jwt_users
            WHERE username = %s""", username)

            user = cursor.fetchone()
            return JwtUser(**user) if user else None

    @classmethod
    def get_by_id(cls, id):
        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            cursor.execute("""
            SELECT
                id,
                username,
                public_key
            FROM jwt_users
            WHERE id = %s""", id)

            user = cursor.fetchone()
            return JwtUser(**user) if user else None
