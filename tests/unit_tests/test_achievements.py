import json
import api
import faf.db as db
import unittest


class AchievementsTestCase(unittest.TestCase):
    def setUp(self):
        api.app.config.from_object('config')
        api.api_init()

        self.app = api.app.test_client()
        db.init_db(api.app.config)

        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute('TRUNCATE TABLE player_achievements')

    def tearDown(self):
        db.connection.close()
        pass

    def test_achievements_list(self):
        response = self.app.get('/achievements')
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual(63, len(data['items']))
        self.assertEqual('c6e6039f-c543-424e-ab5f-b34df1336e81', data['items'][0]['id'])
        self.assertEqual('Novice', data['items'][0]['name'])
        self.assertEqual('Play 10 games', data['items'][0]['description'])
        self.assertEqual('REVEALED', data['items'][0]['initial_state'])
        self.assertEqual('INCREMENTAL', data['items'][0]['type'])
        self.assertEqual(10, data['items'][0]['total_steps'])
        self.assertEqual(None, data['items'][0]['revealed_icon_url'])
        self.assertEqual(None, data['items'][0]['unlocked_icon_url'])

    def test_achievements_get(self):
        response = self.app.get('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81')
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual('c6e6039f-c543-424e-ab5f-b34df1336e81', data['id'])
        self.assertEqual('Novice', data['name'])
        self.assertEqual('Play 10 games', data['description'])
        self.assertEqual('REVEALED', data['initial_state'])
        self.assertEqual('INCREMENTAL', data['type'])
        self.assertEqual(10, data['total_steps'])
        self.assertEqual(None, data['revealed_icon_url'])
        self.assertEqual(None, data['unlocked_icon_url'])

    def test_achievements_increment_inserts_if_not_existing(self):
        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/increment', data=dict(
            player_id=1, steps=5
        ))
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual('REVEALED', data['current_state'])
        self.assertEqual(5, data['current_steps'])
        self.assertFalse(data['newly_unlocked'])

    def test_achievements_increment_unlocks(self):
        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/increment', data=dict(
            player_id=1, steps=10
        ))
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual('UNLOCKED', data['current_state'])
        self.assertEqual(10, data['current_steps'])
        self.assertTrue(data['newly_unlocked'])

    def test_achievements_increment_unlocks_only_once(self):
        self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/increment', data=dict(
            player_id=1, steps=10
        ))
        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/increment', data=dict(
            player_id=1, steps=1
        ))
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual('UNLOCKED', data['current_state'])
        self.assertEqual(10, data['current_steps'])
        self.assertFalse(data['newly_unlocked'])

    def test_achievements_increment_caps_at_max(self):
        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/increment', data=dict(
            player_id=1, steps=11
        ))
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual('UNLOCKED', data['current_state'])
        self.assertEqual(10, data['current_steps'])
        self.assertTrue(data['newly_unlocked'])

    def test_achievements_increment_increments_if_existing(self):
        self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/increment', data=dict(
            player_id=1, steps=1
        ))

        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/increment', data=dict(
            player_id=1, steps=1
        ))
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual('REVEALED', data['current_state'])
        self.assertEqual(2, data['current_steps'])
        self.assertFalse(data['newly_unlocked'])

    def test_achievements_set_steps_at_least_inserts_if_not_existing(self):
        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/setStepsAtLeast', data=dict(
            player_id=1, steps=5
        ))
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual('REVEALED', data['current_state'])
        self.assertEqual(5, data['current_steps'])
        self.assertFalse(data['newly_unlocked'])

    def test_achievements_set_steps_at_least_updates_if_existing(self):
        self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/setStepsAtLeast', data=dict(
            player_id=1, steps=1
        ))

        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/setStepsAtLeast', data=dict(
            player_id=1, steps=3
        ))
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual('REVEALED', data['current_state'])
        self.assertEqual(3, data['current_steps'])
        self.assertFalse(data['newly_unlocked'])

    def test_achievements_set_steps_at_least_keeps_highest(self):
        self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/setStepsAtLeast', data=dict(
            player_id=1, steps=9
        ))

        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/setStepsAtLeast', data=dict(
            player_id=1, steps=3
        ))
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual('REVEALED', data['current_state'])
        self.assertEqual(9, data['current_steps'])
        self.assertFalse(data['newly_unlocked'])

    def test_achievements_set_steps_at_least_unlocks(self):
        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/setStepsAtLeast', data=dict(
            player_id=1, steps=10
        ))
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual('UNLOCKED', data['current_state'])
        self.assertEqual(10, data['current_steps'])
        self.assertTrue(data['newly_unlocked'])

    def test_achievements_set_steps_at_least_unlocks_only_once(self):
        self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/setStepsAtLeast', data=dict(
            player_id=1, steps=10
        ))
        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/setStepsAtLeast', data=dict(
            player_id=1, steps=1
        ))
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual('UNLOCKED', data['current_state'])
        self.assertEqual(10, data['current_steps'])
        self.assertFalse(data['newly_unlocked'])

    def test_achievements_set_steps_at_least_caps_at_max(self):
        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/setStepsAtLeast', data=dict(
            player_id=1, steps=11
        ))
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual('UNLOCKED', data['current_state'])
        self.assertEqual(10, data['current_steps'])
        self.assertTrue(data['newly_unlocked'])

    def test_achievements_unlock(self):
        response = self.app.post('/achievements/50260d04-90ff-45c8-816b-4ad8d7b97ecd/unlock', data=dict(
            player_id=1
        ))
        data = json.loads(response.get_data(as_text=True))

        self.assertTrue(data['newly_unlocked'])

    def test_achievements_unlock_unlocks_only_once(self):
        self.app.post('/achievements/50260d04-90ff-45c8-816b-4ad8d7b97ecd/unlock', data=dict(
            player_id=1
        ))
        response = self.app.post('/achievements/50260d04-90ff-45c8-816b-4ad8d7b97ecd/unlock', data=dict(
            player_id=1
        ))
        data = json.loads(response.get_data(as_text=True))

        self.assertFalse(data['newly_unlocked'])

    def test_achievements_unlock_unlocking_incremental_fails(self):
        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/unlock', data=dict(
            player_id=1
        ))
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual(400, response.status_code)
        self.assertTrue('message' in data)

    def test_achievements_reveal(self):
        response = self.app.post('/achievements/c6e6039f-c543-424e-ab5f-b34df1336e81/reveal', data=dict(
            player_id=1
        ))
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual('REVEALED', data['current_state'])

    def test_achievements_update_multiple(self):
        request_data = dict(
            player_id=1,
            updates=[
                dict(achievement_id='c6e6039f-c543-424e-ab5f-b34df1336e81', update_type='INCREMENT', steps=10),
                dict(achievement_id='50260d04-90ff-45c8-816b-4ad8d7b97ecd', update_type='UNLOCK'),
                dict(achievement_id='326493d7-ce2c-4a43-bbc8-3e990e2685a1', update_type='REVEAL'),
                dict(achievement_id='7d6d8c55-3e2a-41d0-a97e-d35513af1ec6', update_type='SET_STEPS_AT_LEAST', steps=5)
            ]
        )

        response = self.app.post('/achievements/updateMultiple', headers=[('Content-Type', 'application/json')],
                                 data=json.dumps(request_data))
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
        self.app.post('/achievements/5b7ec244-58c0-40ca-9d68-746b784f0cad/unlock', data=dict(player_id=1))
        self.app.post('/achievements/50260d04-90ff-45c8-816b-4ad8d7b97ecd/unlock', data=dict(player_id=1))

        response = self.app.get('/players/1/achievements')
        data = json.loads(response.get_data(as_text=True))

        self.assertEqual(2, len(data['items']))

        self.assertEqual("50260d04-90ff-45c8-816b-4ad8d7b97ecd", data['items'][0]['achievement_id'])
        self.assertEqual("UNLOCKED", data['items'][0]['state'])
        self.assertEqual(None, data['items'][0]['current_steps'])
        self.assertTrue('create_time' in data['items'][0])
        self.assertTrue('update_time' in data['items'][0])

        self.assertEqual("5b7ec244-58c0-40ca-9d68-746b784f0cad", data['items'][1]['achievement_id'])
        self.assertEqual("UNLOCKED", data['items'][1]['state'])
        self.assertEqual(None, data['items'][1]['current_steps'])
        self.assertTrue('create_time' in data['items'][1])
        self.assertTrue('update_time' in data['items'][1])

if __name__ == '__main__':
    unittest.main()
