import db


class OAuthToken(object):
    # TODO micheljung: I think this class should be moved to faf-db
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.token_type = kwargs.get('token_type')
        self.access_token = kwargs.get('access_token')
        self.refresh_token = kwargs.get('refresh_token')
        self.client_id = kwargs.get('client_id')
        self.scopes = kwargs.get('scopes')
        self.expires = kwargs.get('expires')
        self.user_id = kwargs.get('user_id')

    @classmethod
    def get(cls, **kwargs):
        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            cursor.execute("""
            SELECT
                id, access_token, refresh_token, client_id, scopes, expires, user_id
            FROM oauth_tokens
            WHERE access_token = %s OR refresh_token = %s""", kwargs.get('access_token'), kwargs.get('refresh_token'))

            token = cursor.fetchone()
            return OAuthToken(**token) if token else None

    @classmethod
    def delete(cls, client_id, user_id):
        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            cursor.execute("DELETE FROM oauth_tokens WHERE client_id = %s AND user_id = %s", (client_id, user_id))

    @classmethod
    def insert(cls, **kwargs):
        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute("""
                INSERT INTO oauth_tokens (token_type, access_token, refresh_token, client_id, scopes, expires, user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                           (kwargs.get('token_type'),
                            kwargs.get('access_token'),
                            kwargs.get('refresh_token'),
                            kwargs.get('client_id'),
                            kwargs.get('scopes'),
                            kwargs.get('expires'),
                            kwargs.get('user_id'))
                           )
        return OAuthToken(**kwargs)
