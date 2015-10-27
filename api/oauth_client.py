import faf.db as db


class OAuthClient(object):
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.name = kwargs.get('name')
        self.client_secret = kwargs.get('client_secret')
        self.client_type = kwargs.get('client_type')
        self._redirect_uris = kwargs.get('_redirect_uris')
        self.default_redirect_uri = kwargs.get('default_redirect_uri')
        self._default_scopes = kwargs.get('_default_scopes')

    @property
    def redirect_uris(self):
        if self._redirect_uris:
            return self._redirect_uris.split()
        return []

    @property
    def default_scopes(self):
        if self._default_scopes:
            return self._default_scopes.split()
        return []

    @property
    def client_id(self):
        return self.id

    @classmethod
    def get(cls, client_id):
        with db.connection:
            cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
            cursor.execute("""
            SELECT
                id,
                name,
                client_secret,
                client_type,
                redirect_uris as _redirect_uris,
                default_redirect_uri,
                default_scopes as _default_scopes
            FROM oauth_clients
            WHERE id = %s""", client_id)

            client = cursor.fetchone()
            return OAuthClient(**client) if client else None

    def validate_redirect_uri(self, redirect_uri):
        for uri in self.redirect_uris:
            if redirect_uri.startswith(uri):
                return True

        return False
