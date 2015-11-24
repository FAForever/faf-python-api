class MockOAuthToken:
    def __init__(self, expires, scopes, user=None):
        self.expires = expires
        self.scopes = scopes
        self.user = user
