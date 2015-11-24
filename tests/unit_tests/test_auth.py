from hashlib import sha256
import importlib
import json
import re
import unittest

import faf.db as db
import api


class OAuthTestCase(unittest.TestCase):
    def setUp(self):
        importlib.reload(api)
        importlib.reload(api.oauth_handlers)
        importlib.reload(api.auth)

        api.app.config.from_object('config')
        api.api_init()
        api.app.debug = True

        self.app = api.app.test_client()

        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute('TRUNCATE TABLE login')
            cursor.execute('TRUNCATE TABLE oauth_clients')
            cursor.execute('TRUNCATE TABLE oauth_tokens')

    def tearDown(self):
        db.connection.close()
        pass

    def insert_oauth_client(self, client_id, name, secret, redirect_uris, default_scopes):
        cursor = db.connection.cursor()
        cursor.execute("""INSERT INTO oauth_clients
            (id, name, client_secret, redirect_uris, default_redirect_uri, default_scope)
            VALUES (%s, %s, %s, %s, %s, %s)""", (
            client_id, name, secret, redirect_uris, '', default_scopes
        ))
        return cursor

    def insert_user(self, username, password):
        cursor = db.connection.cursor()
        cursor.execute("""INSERT INTO login
        (login, password, email)
        VALUES (%s, %s, 'example@example.com')""",
                       (username, sha256(password.encode('utf-8')).hexdigest()))

    def test_authorize_flow(self):
        with db.connection:
            self.insert_oauth_client('123', 'test client', '456', 'http://example.com http://localhost ', 'read write')
            self.insert_user('User', '321')

        encoded_redirect_uri = 'http%3A%2F%2Flocalhost%3A1234'
        # Dummy URL as we don't have an actual URL in this unit test
        authorize_url = 'http://localhost/oauth/authorize';

        # Try to authorize, but user isn't logged in
        response = self.app.get('/oauth/authorize?client_id=123&redirect_uri=' + encoded_redirect_uri +
                                '&response_type=code&scope=read%20write', follow_redirects=True)

        # Expect login screen
        self.assertEqual(200, response.status_code)
        self.assertRegex(response.data.decode("utf-8"), ".*<title>Log-in</title>.*")

        # Post login data
        response = self.app.post('/login', data=dict(username='User', password='321', next=authorize_url))
        headers = dict(response.headers)

        # Expect being redirected to the authorize_url URL that was sent along the login
        self.assertEqual(302, response.status_code)
        self.assertRegex(headers['Location'], authorize_url)

        # Try again to authorize (in real, this would be the authorize_url the browser would redirect to)
        response = self.app.get('/oauth/authorize?client_id=123&redirect_uri=' + encoded_redirect_uri
                                + '&response_type=code&scope=read%20write', follow_redirects=True)

        # Expect authorization screen
        self.assertEqual(200, response.status_code)
        self.assertRegex(response.data.decode("utf-8"), ".*<title>Authorizing test client</title>.*")

        # Post "Allow" as if the user clicked it
        response = self.app.post('/oauth/authorize?client_id=123&redirect_uri=' + encoded_redirect_uri
                                 + '&response_type=code&scope=read%20write', data=dict(allow='Allow'))

        # Expect being redirected to redirect_uri
        headers = dict(response.headers)
        self.assertEqual(302, response.status_code)
        # Match the redirect URL plus &code=<some_code>
        self.assertRegex(headers['Location'], "http://localhost:1234\?code=.*")

        code = re.search("http://localhost:1234\?code=(.*)", headers['Location']).group(1)

        response = self.app.post('/oauth/token', data=dict(grant_type='authorization_code', client_id='123', code=code,
                                                           client_secret='456', redirect_uri='http://localhost:1234'))

        # Expect login screen
        self.assertEqual(200, response.status_code)

        data = json.loads(response.data.decode("utf-8"))
        self.assertEqual('Bearer', data['token_type'])
        self.assertEqual('read write', data['scope'])
        self.assertTrue('access_token' in data)
        self.assertTrue('refresh_token' in data)

        refresh_token = data['refresh_token']

        response = self.app.post('/oauth/token', data=dict(grant_type='refresh_token', refresh_token=refresh_token,
                                                           client_id='123', client_secret='456'))

        self.assertEqual(200, response.status_code)

    def test_login_wrong_password(self):
        with db.connection:
            self.insert_user('User', '321')

        response = self.app.post('/login', data=dict(username='User', password='123', next=''))

        # Expect login screen
        self.assertEqual(200, response.status_code)
        self.assertRegex(response.data.decode("utf-8"), ".*<title>Log-in</title>.*")

    def test_login_invalid_redirect_uri(self):
        with db.connection:
            self.insert_oauth_client('123', 'test client', '456', 'http://faforever.com', 'read write')
            self.insert_user('User', '321')

        response = self.app.post('/login', data=dict(username='User', password='321',
                                                     next='http://faforever.com.fake.com'))

        self.assertEqual(400, response.status_code)

if __name__ == '__main__':
    unittest.main()
