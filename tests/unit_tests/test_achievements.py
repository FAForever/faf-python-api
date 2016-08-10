import datetime
import importlib
from unittest.mock import Mock

from faf.api.achievement_schema import AchievementSchema
from faf.api.player_achievement_schema import PlayerAchievementSchema

import api
import json
from api import User
import faf.db as db
import unittest

from api.error import ErrorCode


class AchievementsTestCase(unittest.TestCase):
    def get_token(self, access_token=None, refresh_token=None):
        return Mock(
            user=User(id=1),
            expires=datetime.datetime.now() + datetime.timedelta(hours=1),
            scopes=['read_achievements', 'write_achievements']
        )

    def setUp(self):
        importlib.reload(api)
        importlib.reload(api.oauth_handlers)
        importlib.reload(api.achievements)

        api.app.config.from_object('config')
        api.api_init()
        api.app.debug = True

        api.oauth.tokengetter(self.get_token)

        self.app = api.app.test_client()

        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute('delete from login')
            cursor.execute('delete from player_achievements')

    def tearDown(self):
        db.connection.close()

    def test_achievements_list(self):
        response = self.app.get('/achievements?sort=order')
        self.assertEqual(200, response.status_code)
        result, errors = AchievementSchema().loads(response.get_data(as_text=True), many=True)

        self.assertEqual(57, len(result))
        self.assertEqual('c6e6039f-c543-424e-ab5f-b34df1336e81', result[0]['id'])
        self.assertEqual('Novice', result[0]['name'])
        self.assertEqual('Play 10 games', result[0]['description'])
        self.assertEqual('REVEALED', result[0]['initial_state'])
        self.assertEqual('INCREMENTAL', result[0]['type'])
        self.assertEqual(10, result[0]['total_steps'])
        self.assertEqual("http://content.faforever.com/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81.png", result[0]['revealed_icon_url'])
        self.assertEqual("http://content.faforever.com/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81.png", result[0]['unlocked_icon_url'])

    def test_achievements_get(self):
        response = self.app.get('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81')
        self.assertEqual(200, response.status_code)
        result, errors = AchievementSchema().loads(response.get_data(as_text=True))

        self.assertEqual('c6e6039f-c543-424e-ab5f-b34df1336e81', result['id'])
        self.assertEqual('Novice', result['name'])
        self.assertEqual('Play 10 games', result['description'])
        self.assertEqual('REVEALED', result['initial_state'])
        self.assertEqual('INCREMENTAL', result['type'])
        self.assertEqual(10, result['total_steps'])
        self.assertEqual("http://content.faforever.com/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81.png", result['revealed_icon_url'])
        self.assertEqual("http://content.faforever.com/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81.png", result['unlocked_icon_url'])

    def test_achievements_increment_inserts_if_not_existing(self):
        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/increment', data=dict(steps=5))
        self.assertEqual(200, response.status_code)
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual('REVEALED', data['current_state'])
        self.assertEqual(5, data['current_steps'])
        self.assertFalse(data['newly_unlocked'])

    def test_achievements_increment_unlocks(self):
        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/increment', data=dict(steps=10))
        self.assertEqual(200, response.status_code)
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual('UNLOCKED', data['current_state'])
        self.assertEqual(10, data['current_steps'])
        self.assertTrue(data['newly_unlocked'])

    def test_achievements_increment_unlocks_only_once(self):
        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/increment', data=dict(steps=10))
        self.assertEqual(200, response.status_code)
        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/increment', data=dict(steps=1))
        self.assertEqual(200, response.status_code)
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual('UNLOCKED', data['current_state'])
        self.assertEqual(10, data['current_steps'])
        self.assertFalse(data['newly_unlocked'])

    def test_achievements_increment_standard_achievement_fails(self):
        response = self.app.post('/achievements/50260d04-90ff-45c8-816b-4ad8d7b97ecd/increment', data=dict(steps=10))

        result = json.loads(response.data.decode('utf-8'))

        assert response.status_code == 400
        assert result['errors'][0]['code'] == ErrorCode.ACHIEVEMENT_CANT_INCREMENT_STANDARD.value['code']
        assert result['errors'][0]['meta']['args'] == ['50260d04-90ff-45c8-816b-4ad8d7b97ecd']

    def test_achievements_increment_caps_at_max(self):
        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/increment', data=dict(steps=11))
        self.assertEqual(200, response.status_code)
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual('UNLOCKED', data['current_state'])
        self.assertEqual(10, data['current_steps'])
        self.assertTrue(data['newly_unlocked'])

    def test_achievements_increment_increments_if_existing(self):
        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/increment', data=dict(steps=1))
        self.assertEqual(200, response.status_code)

        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/increment', data=dict(steps=1))
        self.assertEqual(200, response.status_code)
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual('REVEALED', data['current_state'])
        self.assertEqual(2, data['current_steps'])
        self.assertFalse(data['newly_unlocked'])

    def test_achievements_set_steps_at_least_inserts_if_not_existing(self):
        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/setStepsAtLeast',
                                 data=dict(steps=5))
        self.assertEqual(200, response.status_code)
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual('REVEALED', data['current_state'])
        self.assertEqual(5, data['current_steps'])
        self.assertFalse(data['newly_unlocked'])

    def test_achievements_set_steps_at_least_updates_if_existing(self):
        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/setStepsAtLeast',
                                 data=dict(steps=1))
        self.assertEqual(200, response.status_code)

        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/setStepsAtLeast',
                                 data=dict(steps=3))
        self.assertEqual(200, response.status_code)
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual('REVEALED', data['current_state'])
        self.assertEqual(3, data['current_steps'])
        self.assertFalse(data['newly_unlocked'])

    def test_achievements_set_steps_at_least_keeps_highest(self):
        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/setStepsAtLeast',
                                 data=dict(steps=9))
        self.assertEqual(200, response.status_code)

        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/setStepsAtLeast',
                                 data=dict(steps=3))
        self.assertEqual(200, response.status_code)
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual('REVEALED', data['current_state'])
        self.assertEqual(9, data['current_steps'])
        self.assertFalse(data['newly_unlocked'])

    def test_achievements_set_steps_at_least_unlocks(self):
        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/setStepsAtLeast',
                                 data=dict(steps=10))
        self.assertEqual(200, response.status_code)
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual('UNLOCKED', data['current_state'])
        self.assertEqual(10, data['current_steps'])
        self.assertTrue(data['newly_unlocked'])

    def test_achievements_set_steps_at_least_unlocks_only_once(self):
        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/setStepsAtLeast',
                                 data=dict(steps=10))
        self.assertEqual(200, response.status_code)
        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/setStepsAtLeast',
                                 data=dict(steps=1))
        self.assertEqual(200, response.status_code)
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual('UNLOCKED', data['current_state'])
        self.assertEqual(10, data['current_steps'])
        self.assertFalse(data['newly_unlocked'])

    def test_achievements_set_steps_at_least_caps_at_max(self):
        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/setStepsAtLeast',
                                 data=dict(steps=11))
        self.assertEqual(200, response.status_code)
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual('UNLOCKED', data['current_state'])
        self.assertEqual(10, data['current_steps'])
        self.assertTrue(data['newly_unlocked'])

    def test_achievements_unlock(self):
        response = self.app.post('/achievements/50260d04-90ff-45c8-816b-4ad8d7b97ecd/unlock', data=dict())
        self.assertEqual(200, response.status_code)
        data = json.loads(response.get_data(as_text=True))

        self.assertTrue(data['newly_unlocked'])

    def test_achievements_unlock_unlocks_only_once(self):
        response = self.app.post('/achievements/50260d04-90ff-45c8-816b-4ad8d7b97ecd/unlock', data=dict())
        self.assertEqual(200, response.status_code)

        response = self.app.post('/achievements/50260d04-90ff-45c8-816b-4ad8d7b97ecd/unlock', data=dict())
        self.assertEqual(200, response.status_code)
        data = json.loads(response.get_data(as_text=True))

        self.assertFalse(data['newly_unlocked'])

    def test_achievements_unlock_unlocking_incremental_fails(self):
        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/unlock', data=dict())

        result = json.loads(response.data.decode('utf-8'))

        assert response.status_code == 400
        assert result['errors'][0]['code'] == ErrorCode.ACHIEVEMENT_CANT_UNLOCK_INCREMENTAL.value['code']
        assert result['errors'][0]['meta']['args'] == ['c6e6039f-c543-424e-ab5f-b34df1336e81']

    def test_achievements_reveal(self):
        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/reveal', data=dict())
        self.assertEqual(200, response.status_code)
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual('REVEALED', data['current_state'])

    def test_achievements_update_multiple(self):
        request_data = dict(
            updates=[
                dict(achievement_id='c6e6039f-c543-424e-ab5f-b34df1336e81', update_type='INCREMENT', steps=10),
                dict(achievement_id='50260d04-90ff-45c8-816b-4ad8d7b97ecd', update_type='UNLOCK'),
                dict(achievement_id='326493d7-ce2c-4a43-bbc8-3e990e2685a1', update_type='REVEAL'),
                dict(achievement_id='7d6d8c55-3e2a-41d0-a97e-d35513af1ec6', update_type='SET_STEPS_AT_LEAST', steps=5)
            ]
        )

        response = self.app.post('/achievements/updateMultiple', headers=[('Content-Type', 'application/json')],
                                 data=json.dumps(request_data))
        self.assertEqual(200, response.status_code)
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual(4, len(data['updated_achievements']))

        self.assertEqual('c6e6039f-c543-424e-ab5f-b34df1336e81', data['updated_achievements'][0]['achievement_id'])
        self.assertEqual('UNLOCKED', data['updated_achievements'][0]['current_state'])
        self.assertEqual(10, data['updated_achievements'][0]['current_steps'])
        self.assertTrue(data['updated_achievements'][0]['newly_unlocked'])

        self.assertEqual('50260d04-90ff-45c8-816b-4ad8d7b97ecd', data['updated_achievements'][1]['achievement_id'])
        self.assertEqual('UNLOCKED', data['updated_achievements'][1]['current_state'])
        self.assertTrue(data['updated_achievements'][1]['newly_unlocked'])
        self.assertFalse('current_steps' in data['updated_achievements'][1])

        self.assertEqual('326493d7-ce2c-4a43-bbc8-3e990e2685a1', data['updated_achievements'][2]['achievement_id'])
        self.assertEqual('REVEALED', data['updated_achievements'][2]['current_state'])
        self.assertFalse('current_steps' in data['updated_achievements'][2])
        self.assertFalse('newly_unlocked' in data['updated_achievements'][2])

        self.assertEqual('7d6d8c55-3e2a-41d0-a97e-d35513af1ec6', data['updated_achievements'][3]['achievement_id'])
        self.assertEqual(5, data['updated_achievements'][3]['current_steps'])
        self.assertEqual('REVEALED', data['updated_achievements'][3]['current_state'])
        self.assertTrue(data['updated_achievements'][1]['newly_unlocked'])

    def test_achievements_list_player(self):
        response = self.app.post('/achievements/5b7ec244-58c0-40ca-9d68-746b784f0cad/unlock', data=dict(player_id=1))
        self.assertEqual(200, response.status_code)

        response = self.app.post('/achievements/50260d04-90ff-45c8-816b-4ad8d7b97ecd/unlock', data=dict(player_id=1))
        self.assertEqual(200, response.status_code)

        response = self.app.get('/players/1/achievements')
        self.assertEqual(200, response.status_code)
        result, errors = PlayerAchievementSchema().loads(response.get_data(as_text=True), many=True)

        self.assertEqual(2, len(result))

        self.assertEqual("50260d04-90ff-45c8-816b-4ad8d7b97ecd", result[0]['achievement_id'])
        self.assertEqual("UNLOCKED", result[0]['state'])
        self.assertEqual(None, result[0]['current_steps'])
        self.assertTrue('create_time' in result[0])
        self.assertTrue('update_time' in result[0])

        self.assertEqual("5b7ec244-58c0-40ca-9d68-746b784f0cad", result[1]['achievement_id'])
        self.assertEqual("UNLOCKED", result[1]['state'])
        self.assertEqual(None, result[1]['current_steps'])
        self.assertTrue('create_time' in result[1])
        self.assertTrue('update_time' in result[1])


if __name__ == '__main__':
    unittest.main()
