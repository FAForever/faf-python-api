import datetime
import json
import api
import faf.db as db
import unittest
from tests.unit_tests.mock_oauth_token import MockOAuthToken


class EventsTestCase(unittest.TestCase):
    def get_token(self, access_token=None, refresh_token=None):
        return MockOAuthToken(
            expires=datetime.datetime.now() + datetime.timedelta(hours=1),
            scopes=['write_events']
        )

    def setUp(self):
        api.app.config.from_object('config')
        api.api_init()
        api.app.debug = True

        api.oauth.tokengetter(self.get_token)

        self.app = api.app.test_client()
        db.init_db(api.app.config)

        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute('TRUNCATE TABLE player_events')

    def tearDown(self):
        db.connection.close()
        pass

    def test_events_list(self):
        response = self.app.get('/events')
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual(28, len(data['items']))
        self.assertEqual('15b6c19a-6084-4e82-ada9-6c30e282191f', data['items'][0]['id'])
        self.assertEqual('Seraphim wins', data['items'][0]['name'])
        self.assertEqual('NUMERIC', data['items'][0]['type'])
        self.assertEqual(None, data['items'][0]['image_url'])

    def test_record_multiple(self):
        request_data = dict(
            player_id=1,
            updates=[
                dict(event_id='15b6c19a-6084-4e82-ada9-6c30e282191f', update_count=10),
                dict(event_id='1b900d26-90d2-43d0-a64e-ed90b74c3704', update_count=15)
            ]
        )

        response = self.app.post('/events/recordMultiple', headers=[('Content-Type', 'application/json')],
                                 data=json.dumps(request_data))
        self.assertEqual(200, response.status_code)
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual(2, len(data['updated_events']))
        self.assertEqual('15b6c19a-6084-4e82-ada9-6c30e282191f', data['updated_events'][0]['event_id'])
        self.assertEqual(10, data['updated_events'][0]['count'])

        self.assertEqual('1b900d26-90d2-43d0-a64e-ed90b74c3704', data['updated_events'][1]['event_id'])
        self.assertEqual(15, data['updated_events'][1]['count'])


if __name__ == '__main__':
    unittest.main()
