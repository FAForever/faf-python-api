import json

import pytest
from faf import db

testGameName = 'testGame'
testGame2Name = 'testGame2'


@pytest.fixture
def games(request):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("TRUNCATE TABLE game_stats")
        cursor.execute("""INSERT INTO game_stats
        (id, startTime, gameType, gameMod, host, mapId, gameName, validity) VALUES
        (234, now(), '1', 2, 146315, 5091, 'testGame', 1),
        (235, now(), '2', 2, 146315, 5092, 'testGame2', 1),
        (236, now(), '3', 1, 146315, 5092, 'testGame3', 1)""")

    def finalizer():
        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute("TRUNCATE TABLE game_stats")

    request.addfinalizer(finalizer)


@pytest.fixture
def game_players(request):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("TRUNCATE TABLE game_player_stats")
        cursor.execute("""INSERT INTO game_player_stats (id, gameId, playerId, AI, faction, color, team, place,
        mean, deviation, after_mean, after_deviation, score, scoreTime) VALUES
        (1, 234, 146315, 0, 1, 1, 1, 1, 500, 1, 2, 2, 50, now()),
        (2, 234, 146316, 0, 1, 1, 1, 1, 600, 1, 2, 2, 50, now()),
        (3, 234, 146317, 0, 1, 1, 1, 1, 700, 1, 2, 2, 50, now()),
        (4, 234, 146318, 0, 1, 1, 1, 1, 800, 1, 2, 2, 50, now()),
        (5, 235, 146315, 0, 1, 1, 1, 1, 900, 1, 2, 2, 50, now()),
        (7, 236, 146315, 0, 1, 1, 1, 1, 2000, 1, 2, 2, 50, now()),
        (8, 236, 146316, 0, 1, 1, 1, 1, 1500, 1, 2, 2, 50, now())""")

    def finalizer():
        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute("TRUNCATE TABLE game_player_stats")

    request.addfinalizer(finalizer)


@pytest.fixture
def maps(request):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("DELETE FROM table_map")
        cursor.execute("""INSERT INTO table_map(id, name, mapuid) VALUES
        (5091,'testMap1',1),
        (5092,'testMap2',1)""")

    def finalizer():
        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute("DELETE FROM table_map")

    request.addfinalizer(finalizer)


@pytest.fixture
def login(request):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("TRUNCATE TABLE login")
        cursor.execute("""INSERT INTO login (id, login, password, salt, email) VALUES
        (146315, 'testUser1', 'hunter2', 'soSalty', 'a'),
        (146316, 'testUser2', 'hunter2', 'soSalty', 'b'),
        (146317, 'testUser3', 'hunter2', 'soSalty', 'c'),
        (146318, 'testUser4', 'hunter2', 'soSalty', 'd')""")

    def finalizer():
        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute("TRUNCATE TABLE login")

    request.addfinalizer(finalizer)


@pytest.fixture
def ladder(request):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("TRUNCATE TABLE ladder1v1_rating")
        cursor.execute("""INSERT INTO ladder1v1_rating (id, mean, deviation, numGames, winGames, is_active) VALUES
        (146315, 2000, 0, 0, 0, 0),
        (146316, 1500, 0, 0, 0, 0),
        (146317, 500, 0, 0, 0, 0),
        (146318, 700, 0, 0, 0, 0)""")

    def finalizer():
        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute("TRUNCATE TABLE ladder1v1_rating")

    request.addfinalizer(finalizer)


def test_games(test_client, games):
    response = test_client.get('/games')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 3

    for item in result['data']:
        assert 'id' in item
        assert 'type' in item
        assert 'game_name' in item['attributes']
        assert 'map_id' in item['attributes']
        assert 'victory_condition' in item['attributes']
        assert 'game_mod' in item['attributes']
        assert 'host' in item['attributes']
        assert 'start_time' in item['attributes']
        assert 'validity' in item['attributes']
        assert item['type'] == 'game_stats'


def test_games_no_games(test_client):
    response = test_client.get('/games')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    assert len(result['data']) == 0


def test_games_query_one_player(test_client, games, game_players, login):
    response = test_client.get('/games?filter[players]=testUser2')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    assert len(result['data']) == 2
    assert result['data'][0]['id'] == '234'
    assert result['data'][1]['id'] == '236'


def test_games_query_multiple_players(test_client, games, game_players, login):
    response = test_client.get('/games?filter[players]=testUser1,testUser3')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    assert len(result['data']) == 1
    assert result['data'][0]['id'] == '234'


def test_games_query_player_no_result(test_client, games, game_players, login):
    response = test_client.get('/games?filter[players]=unknownUser')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    assert len(result['data']) == 0


def test_games_query_map_name(test_client, maps, game_players, games):
    response = test_client.get('/games?filter[map_name]=testMap1')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    assert len(result['data']) == 1
    assert result['data'][0]['id'] == '234'


def test_games_query_map_name_exclude(test_client, maps, game_players, games):
    response = test_client.get('/games?filter[map_name]=testMap1&filter[map_exclude]=true')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    assert len(result['data']) == 2
    assert result['data'][0]['id'] == '235'
    assert result['data'][1]['id'] == '236'


def test_games_query_map_exclude(test_client):
    response = test_client.get('/games?filter[map_exclude]=true')

    assert response.status_code == 422
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    assert 'errors' in result


def test_games_query_max_rating(test_client, games, game_players):
    response = test_client.get('/games?filter[max_rating]=1000')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    assert len(result['data']) == 2
    assert result['data'][0]['id'] == '234'
    assert result['data'][1]['id'] == '235'


def test_games_query_min_rating(test_client, games, game_players):
    response = test_client.get('/games?filter[min_rating]=1100')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    assert len(result['data']) == 1
    assert result['data'][0]['id'] == '236'


def test_games_query_max_and_min_rating(test_client, games, game_players):
    response = test_client.get('/games?filter[max_rating]=800&filter[min_rating]=500')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    assert len(result['data']) == 1
    assert result['data'][0]['id'] == '234'


def test_games_query_rating_type_and_no_rating(test_client, games, game_players):
    response = test_client.get('/games?filter[rating_type]=global')

    assert response.status_code == 422
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    assert 'errors' in result


def test_games_query_min_and_max_rating_ladder(test_client, games, game_players, ladder):
    response = test_client.get('/games?filter[max_rating]=800&filter[min_rating]=500&filter[rating_type]=ladder')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    assert len(result['data']) == 1
    assert result['data'][0]['id'] == '234'


def test_games_query_game_type(test_client, games, game_players):
    response = test_client.get('/games?filter[game_type]=1')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    assert len(result['data']) == 1
    assert result['data'][0]['id'] == '234'


def test_game_id_no_players(test_client, games):
    response = test_client.get('/games/235')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['relationships']['players']['data']) == 0
    assert result['data']['id'] == '235'
    assert result['data']['attributes']['game_name'] == testGame2Name
    assert result['data']['attributes']['validity'] == 'TOO_MANY_DESYNCS'
    assert result['data']['attributes']['victory_condition'] == 'ERADICATION'


def test_game_id_four_players(test_client, games, game_players):
    response = test_client.get('/games/234')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['relationships']['players']['data']) == 4
    assert result['data']['id'] == '234'
    assert result['data']['attributes']['game_name'] == testGameName

    for item in result['relationships']['players']['data']:
        assert 'id' in item
        assert 'type' in item
        assert item['type'] == 'game_player_stats'


def test_game_id_no_game(test_client, games, game_players):
    response = test_client.get('/games/0')

    assert response.status_code == 404
    assert response.content_type == 'application/vnd.api+json'

    data = json.loads(response.data.decode('utf-8'))

    assert 'errors' in data


def test_game_id_players_relationship_four_players(test_client, games, game_players):
    response = test_client.get('/games/234/players')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 4

    for item in result['data']:
        assert 'attributes' in item
        assert 'team' in item['attributes']
        assert 'faction' in item['attributes']
        assert 'mean' in item['attributes']
        assert 'deviation' in item['attributes']
        assert 'id' in item
        assert 'type' in item
        assert item['type'] == 'game_player_stats'


def test_game_id_players_relationship_no_game(test_client, games, game_players):
    response = test_client.get('/games/0/players')

    assert response.status_code == 404
    assert response.content_type == 'application/vnd.api+json'

    data = json.loads(response.data.decode('utf-8'))

    assert 'errors' in data


def test_games_page_size(test_client, games):
    response = test_client.get('/games?page[size]=1')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 1
    assert result['data'][0]['attributes']['game_name'] == testGameName


def test_games_invalid_page_size(test_client, games):
    response = test_client.get('/games?page[size]=1001')

    assert response.status_code == 400
    assert json.loads(response.get_data(as_text=True))['message'] == 'Invalid page size'


def test_games_query_players_sql_injection(test_client):
    response = test_client.get("/games?filter[players]=' or%201=1; --")

    assert response.status_code == 200
    result = json.loads(response.data.decode('utf-8'))
    assert len(result['data']) == 0


def test_games_query_map_name_sql_injection(test_client):
    response = test_client.get("/games?filter[map_exclude]=true&filter[map_name]=' or%201=1; --")

    assert response.status_code == 200
    result = json.loads(response.data.decode('utf-8'))
    assert len(result['data']) == 0


def test_games_query_max_rating_sql_injection(test_client):
    response = test_client.get("/games?filter[max_rating]=' or%201=1; --&filter[rating_type]=hey")

    assert response.status_code == 400
    result = json.loads(response.data.decode('utf-8'))
    assert 'message' in result


def test_games_query_min_rating_sql_injection(test_client):
    response = test_client.get("/games?filter[min_rating]=' or%201=1; --&filter[rating_type]=hey")

    assert response.status_code == 400
    result = json.loads(response.data.decode('utf-8'))
    assert 'message' in result


def test_games_query_game_type_sql_injection(test_client):
    response = test_client.get("/games?filter[game_type]=' or%201=1;")

    assert response.status_code == 200
    result = json.loads(response.data.decode('utf-8'))
    assert len(result['data']) == 0


def test_games_query_invalid_map_exclude(test_client):
    response = test_client.get('/games?filter[map_exclude]=hey&filter[map_name]=hey')

    assert response.status_code == 400
    result = json.loads(response.data.decode('utf-8'))
    assert 'message' in result
