import datetime
import importlib
import json

from faf.api.event_schema import EventSchema

import api
from api import User
from api.oauth_token import OAuthToken
import faf.db as db
import unittest


class EventsTestCase(unittest.TestCase):
    def get_token(self, access_token=None, refresh_token=None):
        return OAuthToken(
            user=User(id=1),
            client_id=1,
            expires=datetime.datetime.now() + datetime.timedelta(hours=1),
            scopes=['write_events']
        )

    def setUp(self):
        importlib.reload(api)
        importlib.reload(api.oauth_handlers)
        importlib.reload(api.events)

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
        response = self.app.get('/events?sort=id')
        self.assertEqual(200, response.status_code)
        result, errors = EventSchema().loads(response.get_data(as_text=True), many=True)

        self.assertEqual(28, len(result))
        self.assertEqual('15b6c19a-6084-4e82-ada9-6c30e282191f', result[0]['id'])
        self.assertEqual('Seraphim wins', result[0]['name'])
        self.assertEqual('NUMERIC', result[0]['type'])
        self.assertEqual(None, result[0]['image_url'])

    def test_events_record(self):
        response = self.app.post('/events/15b6c19a-6084-4e82-ada9-6c30e282191f/record', data=dict(count=5))
        self.assertEqual(200, response.status_code)
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual(5, data['count'])

    def test_record_multiple(self):
        request_data = dict(
            player_id=1,
            updates=[
                dict(event_id='15b6c19a-6084-4e82-ada9-6c30e282191f', count=10),
                dict(event_id='1b900d26-90d2-43d0-a64e-ed90b74c3704', count=15)
            ]
        )

        response = self.app.post('/events/recordMultiple', headers=[('Content-Type', 'application/json')],
                                 data=json.dumps(request_data))
        self.assertEqual(200, response.status_code)
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual(2, len(data['updated_events']))
        self.assertEqual(10, data['updated_events'][0]['count'])

        self.assertEqual(15, data['updated_events'][1]['count'])


if __name__ == '__main__':
    unittest.main()
