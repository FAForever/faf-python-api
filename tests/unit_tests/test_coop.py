import datetime
import importlib
import json
import os
from io import BytesIO

from unittest.mock import Mock

import pytest
import sys

from pymysql.cursors import DictCursor

import api
from api import User
from api.error import ErrorCode
from faf import db


@pytest.fixture
def test_data(request):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("TRUNCATE TABLE game_player_stats")
        cursor.execute("TRUNCATE TABLE game_stats")
        cursor.execute("TRUNCATE TABLE coop_leaderboard")
        cursor.execute("TRUNCATE TABLE coop_map")
        cursor.execute("DELETE FROM game_featuredMods")
        cursor.execute("DELETE FROM login")
        # TODO use common fixtures
        cursor.execute("""INSERT INTO login
        (id, login, password, email) VALUES
        (1, 'a', '', 'a'),
        (2, 'b', '', 'b'),
        (3, 'c', '', 'c'),
        (4, 'd', '', 'd')""")
        cursor.execute("""insert into coop_map (id, name, description, version, type, filename)
        values
        (1, 'SCMP 001', 'Description 1', 1, 1, 'maps/scmp_001.v0001.zip'),
        (2, 'SCMP 002', 'Description 2', 2, 1, 'maps/scmp_002.v0002.zip'),
        (3, 'SCMP 003', 'Description 3', 2, 1, 'maps/scmp_003.v0002.zip')""")
        cursor.execute("""insert into coop_leaderboard (id, mission, gameuid, secondary, time, player_count)
        values
        (1, 1, 1, 1, '00:39', 2),
        (2, 1, 2, 1, '00:45', 1),
        (3, 1, 3, 0, '00:36', 2),
        (4, 2, 4, 1, '00:21', 3)""")
        cursor.execute("""INSERT INTO game_featuredMods
        (id, gamemod, description, name, publish, `order`) VALUES
        (25, 'coop', '', '', 1, 1)
        """)
        cursor.execute("""INSERT INTO game_stats
        (id, startTime, gameType, gameMod, host, mapId, gameName, validity) VALUES
        (1, '2016-10-12T11:40', 1, 25, 1, 1, '', 11),
        (2, '2016-10-12T12:40', 1, 25, 1, 1, '', 11),
        (3, '2016-10-12T13:40', 1, 25, 1, 1, '', 11),
        (4, '2016-10-12T14:40', 1, 25, 1, 1, '', 11)
        """)
    cursor.execute("""INSERT INTO game_player_stats
(id, gameId, playerId, AI, faction, color, team, place, mean, deviation, after_mean, after_deviation, score,          scoreTime) VALUES
(1,       1,        1,  0,       1,     1,    1,     1, 1500,       123,        NULL,             NULL,   0, '2016-10-12T11:51'),
(2,       1,        2,  0,       1,     1,    1,     2, 1395,       111,        NULL,             NULL,   0, '2016-10-12T12:51'),
(3,       2,        1,  0,       1,     1,    1,     1, 1390,       110,        NULL,             NULL,   0, '2016-10-12T13:51'),
(4,       3,        3,  0,       1,     1,    1,     1, 1401,       110,        NULL,             NULL,   0, '2016-10-12T14:51'),
(5,       3,        4,  0,       1,     1,    1,     2, 1500,       250,        NULL,             NULL,   0, '2016-10-12T14:51'),
(6,       4,        1,  0,       1,     1,    1,     1, 1400,       150,        NULL,             NULL,   0, '2016-10-12T15:51'),
(7,       4,        2,  0,       1,     1,    1,     2, 1500,       250,        NULL,             NULL,   0, '2016-10-12T16:51'),
(8,       4,        3,  0,       1,     1,    1,     3, 1500,       250,        NULL,             NULL,   0,               NULL)
        """)

    def finalizer():
        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute("TRUNCATE TABLE coop_leaderboard")
            cursor.execute("TRUNCATE TABLE coop_map")

    request.addfinalizer(finalizer)


@pytest.fixture
def oauth():
    def get_token(access_token=None, refresh_token=None):
        return Mock(
            user=User(id=1),
            expires=datetime.datetime.now() + datetime.timedelta(hours=1),
            scopes=['']
        )

    importlib.reload(api)
    importlib.reload(api.oauth_handlers)
    importlib.reload(api.coop)

    api.app.config.from_object('config')
    api.api_init()
    api.app.debug = True

    api.oauth.tokengetter(get_token)

    return api.app.test_client()


def test_coop_missions(test_client, test_data):
    response = test_client.get('/coop/missions')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) > 0

    for item in result['data']:
        assert 'type' in item
        assert 'name' in item['attributes']
        assert 'description' in item['attributes']
        assert 'category' in item['attributes']
        assert 'version' in item['attributes']
        assert 'download_url' in item['attributes']
        assert 'thumbnail_url_small' in item['attributes']
        assert 'thumbnail_url_large' in item['attributes']
        assert 'folder_name' in item['attributes']


def test_coop_missions_fields(test_client, test_data):
    response = test_client.get('/coop/missions?fields[coop_mission]=name')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 3
    assert len(result['data'][0]['attributes']) == 1

    for item in result['data']:
        assert 'name' in item['attributes']
        assert 'version' not in item['attributes']


def test_coop_missions_fields_two(test_client, test_data):
    response = test_client.get('/coop/missions?fields[coop_mission]=name,version')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 3
    assert len(result['data'][0]['attributes']) == 2

    for item in result['data']:
        assert 'name' in item['attributes']
        assert 'version' in item['attributes']
        assert 'category' not in item['attributes']
        assert 'description' not in item['attributes']


def test_coop_missions_page_size(test_client, test_data):
    response = test_client.get('/coop/missions?page[size]=1')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 1


def test_coop_missions_invalid_page_size(test_client, test_data):
    response = test_client.get('/coop/missions?page[size]=1001')

    assert response.status_code == 400
    result = json.loads(response.get_data(as_text=True))
    assert len(result['errors']) == 1
    assert result['errors'][0]['code'] == ErrorCode.QUERY_INVALID_PAGE_SIZE.value['code']


def test_coop_missions_page(test_client, test_data):
    response = test_client.get('/coop/missions?page[size]=1&page[number]=2')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 1
    assert result['data'][0]['attributes']['name'] == 'SCMP 002'


def test_coop_missions_invalid_page(test_client, test_data):
    response = test_client.get('/coop/missions?page[number]=-1')

    result = json.loads(response.data.decode('utf-8'))

    assert response.status_code == 400
    assert result['errors'][0]['code'] == ErrorCode.QUERY_INVALID_PAGE_NUMBER.value['code']
    assert result['errors'][0]['meta']['args'] == [-1]


def test_coop_missions_sort_by_version(test_client, test_data):
    response = test_client.get('/coop/missions?sort=-version')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['data']) > 0

    previous_version = sys.maxsize
    for item in result['data']:
        assert item['attributes']['version'] <= previous_version
        previous_version = item['attributes']['version']


def test_coop_missions_inject_sql_sort(test_client):
    response = test_client.get('/coop/missions?sort=or%201=1')

    assert response.status_code == 400
    result = json.loads(response.get_data(as_text=True))
    assert len(result['errors']) == 1
    assert result['errors'][0]['code'] == ErrorCode.QUERY_INVALID_SORT_FIELD.value['code']
    assert result['errors'][0]['meta']['args'] == ['or 1=1']


def test_coop_leaderboards_player_count_two(test_client, test_data):
    response = test_client.get('/coop/leaderboards/1/2')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert result == {'data': [
        {
            'id': 3,
            'type': 'coop_leaderboard',
            'attributes': {
                'ranking': 1,
                'id': 3,
                'secondary_objectives': False,
                'player_names': 'c, d',
                'duration': 2160
            }
        }, {
            'id': 1,
            'type': 'coop_leaderboard',
            'attributes': {
                'ranking': 2,
                'id': 1,
                'secondary_objectives': True,
                'player_names': 'a, b',
                'duration': 2340
            }
        }
    ]}


@pytest.mark.parametrize("player_count", [0, -1])
def test_coop_leaderboards_player_count_all(test_client, test_data, player_count):
    response = test_client.get('/coop/leaderboards/1/0')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert result == {'data': [{
        'attributes': {
            'secondary_objectives': False,
            'player_names': 'c, d',
            'ranking': 1,
            'duration': 2160,
            'id': 3
        }, 'id': 3,
        'type': 'coop_leaderboard'
    }, {
        'attributes': {
            'secondary_objectives': True,
            'player_names': 'a, b',
            'ranking': 2,
            'duration': 2340,
            'id': 1
        }, 'id': 1,
        'type': 'coop_leaderboard'
    }, {
        'attributes': {
            'secondary_objectives': True,
            'player_names': 'a',
            'ranking': 3,
            'duration': 2700,
            'id': 2
        }, 'id': 2,
        'type': 'coop_leaderboard'
    }]}
