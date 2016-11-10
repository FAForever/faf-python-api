import datetime
import importlib
import json
from unittest.mock import Mock

import pytest

import api
from faf import db
from api import User


@pytest.fixture
def test_data(request, app):
    app.debug = True
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("TRUNCATE TABLE ladder1v1_rating")
        cursor.execute("TRUNCATE TABLE global_rating")
        cursor.execute("delete from avatars")
        cursor.execute("delete from login")
        cursor.execute("delete from game_player_stats")
        cursor.execute("delete from game_stats")
        cursor.execute("delete from game_featuredMods")
        # TODO use common fixtures
        cursor.execute("""INSERT INTO login
        (id, login, password, email) VALUES
        (1, 'a', '', 'a'),
        (2, 'b', '', 'b'),
        (3, 'c', '', 'c'),
        (4, 'd', '', 'd')""")
        cursor.execute("""INSERT INTO ladder1v1_rating
        (id, mean, deviation, numGames, winGames, is_active) VALUES
        (1, 1000, 300, 10, 5, 0),
        (2, 2000, 200, 20, 9, 1),
        (3, 1720, 100, 13, 7, 1),
        (4, 1500, 99, 30, 17, 1)""")
        cursor.execute("""INSERT INTO global_rating
        (id, mean, deviation, numGames, is_active) VALUES
        (1, 800, 100, 5, 0),
        (2, 500, 300, 2, 1),
        (3, 1600, 200, 3, 1),
        (4, 1800, 50, 20, 1)""")
        cursor.execute("""INSERT INTO game_featuredMods
        (id, gamemod, description, name, publish, `order`) VALUES
        (1, 'faf', '', '', 1, 1),
        (2, 'ladder1v1', '', '', 1, 1),
        (3, 'blackops', '', '', 1, 1)
        """)
        cursor.execute("""INSERT INTO game_stats
        (id, startTime, gameType, gameMod, host, mapId, gameName, validity) VALUES
        (1, '2016-10-12T11:40', 1, 2, 1, 1, '', 0),
        (2, '2016-10-12T12:40', 1, 1, 1, 1, '', 0),
        (3, '2016-10-12T13:40', 1, 1, 1, 1, '', 0),
        (4, '2016-10-12T14:40', 1, 1, 1, 1, '', 0),
        (5, '2016-10-12T15:40', 1, 1, 1, 1, '', 0),
        (6, '2016-10-12T16:40', 1, 3, 1, 1, '', 0),
        (7, '2016-10-12T17:40', 1, 1, 1, 1, '', 0)
        """)
        cursor.execute("""INSERT INTO game_player_stats
(id, gameId, playerId, AI, faction, color, team, place, mean, deviation, after_mean, after_deviation, score,          scoreTime) VALUES
(1,       1,        1,  0,       1,     1,    1,     1, 1500,       123,         800,             100,    0, '2016-10-12T11:51'),
(2,       2,        1,  0,       1,     1,    1,     1, 1395,       111,        1390,             110,    0, '2016-10-12T12:51'),
(3,       3,        1,  0,       1,     1,    1,     1, 1390,       110,        1401,             150,    0, '2016-10-12T13:51'),
(4,       4,        1,  0,       1,     1,    1,     1, 1401,       110,        1405,             149,    0, '2016-10-12T14:51'),
(5,       4,        2,  0,       1,     1,    1,     1, 1500,       250,        1400,             150,    0, '2016-10-12T14:51'),
(6,       5,        1,  0,       1,     1,    1,     1, 1400,       150,        NULL,             NULL,   0, '2016-10-12T15:51'),
(7,       5,        2,  0,       1,     1,    1,     2, 1400,       150,        NULL,             NULL,   0, '2016-10-12T15:51'),
(8,       6,        1,  0,       1,     1,    1,     2, 1500,       250,        NULL,             NULL,   0, '2016-10-12T16:51'),
(9,       7,        1,  0,       1,     1,    1,     2, 1500,       250,        1500,              250,   0,               NULL)
        """)


@pytest.fixture
def oauth():
    def get_token(access_token=None, refresh_token=None):
        return Mock(
            user=User(id=1),
            expires=datetime.datetime.now() + datetime.timedelta(hours=1),
            scopes=['public_profile']
        )

    importlib.reload(api)
    importlib.reload(api.oauth_handlers)
    importlib.reload(api.players)

    api.app.config.from_object('config')
    api.api_init()
    api.app.debug = True

    api.oauth.tokengetter(get_token)

    return api.app.test_client()


def test_players_global_history(test_client, test_data):
    response = test_client.get('/players/1/ratings/global/history')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert result['data']['attributes']['history'] == {
        '1476280260': [1401.0, 150.0],
        '1476276660': [1390.0, 110.0],
        '1476283860': [1405.0, 149.0]
    }


def test_players_1v1_history(test_client, test_data):
    response = test_client.get('/players/1/ratings/1v1/history')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert result['data']['attributes']['history'] == {
        '1476273060': [800.0, 100.0]
    }


def test_get_player(test_client, test_data):
    response = test_client.get('/players/2')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert result['data']['attributes'] == {
        'id': '2',
        'login': 'b'
    }


def test_get_player_me(oauth, test_data):
    response = oauth.get('/players/me')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert result['data']['attributes'] == {
        'id': '1',
        'login': 'a'
    }
