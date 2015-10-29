from oauthlib.oauth2.rfc6749 import utils
from api.user import User
import faf.db as db


class OAuthToken(object):
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.token_type = kwargs.get('token_type')
        self.access_token = kwargs.get('access_token')
        self.refresh_token = kwargs.get('refresh_token')
        self.client_id = kwargs.get('client_id')
        self.expires = kwargs.get('expires')
        self.user = User.get_by_id(kwargs.get('user_id')) if kwargs.get('user') is None else kwargs.get('user')
        self.scope = self.get_scope_string(**kwargs)

    @property
    def scopes(self):
        return utils.scope_to_list(self.scope)

    @classmethod
    def get(cls, **kwargs):
        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            cursor.execute("""
            SELECT
                id, token_type, access_token, refresh_token, client_id, scope, expires, user_id
            FROM oauth_tokens
            WHERE access_token = %s OR refresh_token = %s""", (kwargs.get('access_token'), kwargs.get('refresh_token')))

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
    INSERT INTO oauth_tokens (token_type, access_token, refresh_token, client_id, scope, expires, user_id)
    VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                           (kwargs.get('token_type'),
                            kwargs.get('access_token'),
                            kwargs.get('refresh_token'),
                            kwargs.get('client_id'),
                            cls.get_scope_string(**kwargs),
                            kwargs.get('expires'),
                            kwargs.get('user_id'))
                           )
        return OAuthToken(**kwargs)

    @staticmethod
    def get_scope_string(**kwargs):
        if 'scopes' in kwargs:
            return utils.list_to_scope(kwargs.get('scopes'))
        elif 'scope' in kwargs:
            return kwargs.get('scope')
