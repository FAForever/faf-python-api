import json

import pytest
from faf.api import LeaderboardSchema

from api.error import ErrorCode
from faf import db


@pytest.fixture
def rating_ratings(request, app):
    app.debug = True
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("TRUNCATE TABLE ladder1v1_rating")
        cursor.execute("TRUNCATE TABLE global_rating")
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

    def finalizer():
        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute("TRUNCATE TABLE ladder1v1_rating")

    request.addfinalizer(finalizer)


def test_leaderboards_1v1(test_client, rating_ratings):
    response = test_client.get('/leaderboards/1v1')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 3

    for item in result['data']:
        assert 'type' in item


def test_leaderboards_global(test_client, rating_ratings):
    response = test_client.get('/leaderboards/1v1/4')
    schema = LeaderboardSchema()

    result, errors = schema.loads(response.data.decode('utf-8'))

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'
    assert not errors
    assert result['login'] == 'd'
    assert result['ranking'] == 1


def test_leaderboards_not_found(test_client, rating_ratings):
    response = test_client.get('/leaderboards/1v1/999')

    assert response.status_code == 404
    assert response.content_type == 'application/vnd.api+json'

    data = json.loads(response.data.decode('utf-8'))

    assert 'errors' in data


def test_leaderboards_page_size(test_client, rating_ratings):
    response = test_client.get('/leaderboards/1v1?page[size]=1')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 1


def test_leaderboards_invalid_page_size(test_client, rating_ratings):
    response = test_client.get('/leaderboards/1v1?page[size]=5001')

    result = json.loads(response.data.decode('utf-8'))

    assert response.status_code == 400
    assert result['errors'][0]['code'] == ErrorCode.QUERY_INVALID_PAGE_SIZE.value['code']
    assert result['errors'][0]['meta']['args'] == [5001]


def test_leaderboards_page(test_client, rating_ratings):
    response = test_client.get('/leaderboards/1v1?page[size]=1&page[number]=2')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 1
    assert result['data'][0]['attributes']['login'] == 'b'
    assert result['data'][0]['attributes']['ranking'] == 2


def test_leaderboards_invalid_page(test_client):
    response = test_client.get('/leaderboards/1v1?page[number]=-1')

    result = json.loads(response.data.decode('utf-8'))

    assert response.status_code == 400
    assert result['errors'][0]['code'] == ErrorCode.QUERY_INVALID_PAGE_NUMBER.value['code']
    assert result['errors'][0]['meta']['args'] == [-1]


def test_leaderboards_sort_disallowed(test_client):
    response = test_client.get('/leaderboards/1v1?sort=mean')

    result = json.loads(response.data.decode('utf-8'))

    assert response.status_code == 400
    assert result['errors'][0]['code'] == ErrorCode.QUERY_INVALID_SORT_FIELD.value['code']
    assert result['errors'][0]['meta']['args'] == ['mean']


def test_leaderboards_1v1_stats(test_client, rating_ratings):
    response = test_client.get('/leaderboards/1v1/stats')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert result['data']['attributes']['rating_distribution'] == {'1200': 1, '1400': 2}


def test_leaderboards_global_stats(test_client, rating_ratings):
    response = test_client.get('/leaderboards/global/stats')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert result['data']['attributes']['rating_distribution'] == {'1000': 1, '1600': 1}


def test_leaderboards_invalid(test_client, rating_ratings):
    response = test_client.get('/leaderboards/')

    assert response.status_code == 404


def test_leaderboards_get_player_invalid(test_client, rating_ratings):
    response = test_client.get('/leaderboards/lol/1')

    result = json.loads(response.data.decode('utf-8'))

    assert response.status_code == 400
    assert result['errors'][0]['detail'] == 'Rating type is not valid: lol. Please pick "1v1" or "global".'
    assert result['errors'][0]['title'] == ErrorCode.QUERY_INVALID_RATING_TYPE.value['title']
    assert result['errors'][0]['meta']['args'] == ['lol']


def test_leaderboards_get_player_1v1(test_client, rating_ratings):
    response = test_client.get('/leaderboards/1v1/1')

    schema = LeaderboardSchema()

    result, errors = schema.loads(response.data.decode('utf-8'))

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'
    assert not errors
    assert result['login'] == 'a'
    assert result['ranking'] == 1


def test_leaderboards_get_player_global(test_client, rating_ratings):
    response = test_client.get('/leaderboards/global/1')

    schema = LeaderboardSchema()

    result, errors = schema.loads(response.data.decode('utf-8'))

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'
    assert not errors
    assert result['login'] == 'a'
    assert result['ranking'] == 2


def test_leaderboards_global_history(test_client, rating_ratings):
    response = test_client.get('/leaderboards/global/1/history')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert result['data']['attributes']['history'] == {
        '1476280260': [1401.0, 150.0],
        '1476276660': [1390.0, 110.0],
        '1476283860': [1405.0, 149.0]
    }


def test_leaderboards_1v1_history(test_client, rating_ratings):
    response = test_client.get('/leaderboards/1v1/1/history')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert result['data']['attributes']['history'] == {
        '1476273060': [800.0, 100.0]
    }
