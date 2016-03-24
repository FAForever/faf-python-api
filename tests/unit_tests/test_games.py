import json

import pytest
from faf import db

testGameName = 'testGame'
testGame2Name = 'testGame2'
testGame3Name = 'testGame3'
testGame4Name = 'testGame4'


@pytest.fixture
def game_stats(request):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("TRUNCATE TABLE game_stats")
        cursor.execute("""INSERT INTO game_stats
        (id, startTime, gameType, gameMod, host, mapId, gameName, validity) VALUES
        (234, '1997-07-16T19:20', '1', 1, 146315, 5091, 'testGame', 1),
        (235, '1997-07-19T19:20', '2', 2, 146315, 5092, 'testGame2', 1),
        (236, '1997-07-21T19:20', '3', 3, 146315, 5092, 'testGame3', 1),
        (237, '1997-07-24T19:20', '4', 2, 146315, 5093, 'testGame4', 1)""")

    def finalizer():
        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute("TRUNCATE TABLE game_stats")

    request.addfinalizer(finalizer)


@pytest.fixture
def game_player_stats(request):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("TRUNCATE TABLE game_player_stats")
        cursor.execute("""INSERT INTO game_player_stats (id, gameId, playerId, AI, faction, color, team, place,
        mean, deviation, after_mean, after_deviation, score, scoreTime) VALUES
        (1, 234, 146315, 0, 1, 1, 1, 1, 0, 1, 2, 2, 50, '1997-07-16T19:20'),
        (2, 234, 146316, 0, 1, 1, 1, 1, 0, 1, 2, 2, 50, '1997-07-16T19:20'),
        (3, 234, 146317, 0, 1, 1, 1, 1, 0, 1, 2, 2, 50, '1997-07-16T19:20'),
        (4, 234, 146318, 0, 1, 1, 1, 1, 0, 1, 2, 2, 50, '1997-07-17T19:20'),
        (5, 235, 146316, 0, 1, 1, 1, 1, 0, 1, 2, 2, 50, now()),
        (7, 236, 146315, 0, 1, 1, 1, 1, 0, 1, 2, 2, 50, now()),
        (8, 236, 146316, 0, 1, 1, 1, 1, 0, 1, 2, 2, 50, now()),
        (9, 237, 146317, 0, 1, 1, 1, 1, 0, 1, 2, 2, 50, now()),
        (10, 237, 146318, 0, 1, 1, 1, 1, 0, 1, 2, 2, 50, now())""")

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
        (5092,'testMap2',1),
        (5093,'testMap3',1)""")

    def finalizer():
        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute("DELETE FROM table_map")

    request.addfinalizer(finalizer)


@pytest.fixture
def mods(request):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("DELETE FROM game_featuredMods")
        cursor.execute("""INSERT INTO game_featuredMods(id, name) VALUES
        (1,'gfmod1'),
        (2,'gfmod2'),
        (3,'gfmod3')""")

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


@pytest.fixture
def global_rating(request):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("TRUNCATE TABLE global_rating")
        cursor.execute("""INSERT INTO global_rating (id, mean, deviation, numGames, is_active) VALUES
        (146315, 3000, 0, 0, 0),
        (146316, 2000, 0, 0, 0),
        (146317, 1000, 0, 0, 0),
        (146318, 500, 0, 0, 0)""")

    def finalizer():
        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute("TRUNCATE TABLE global_rating")

    request.addfinalizer(finalizer)


def test_games(test_client, game_stats, game_player_stats, global_rating, maps, mods, login):
    response = test_client.get('/games')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 4

    for item in result['data']:
        assert 'id' in item
        assert 'type' in item
        assert 'game_name' in item['attributes']
        assert 'map_name' in item['attributes']
        assert 'map_id' in item['attributes']
        assert 'victory_condition' in item['attributes']
        assert 'mod_name' in item['attributes']
        assert 'mod_id' in item['attributes']
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


def test_games_query_one_player(test_client, game_stats, game_player_stats, login, global_rating, maps, mods):
    response = test_client.get('/games?filter[players]=testUser2')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    results_data = result['data']
    assert len(results_data) == 3
    assert results_data[0]['id'] == '236'
    assert results_data[1]['id'] == '235'
    assert results_data[2]['id'] == '234'
    player_data_1 = results_data[0]['relationships']['players']['data']
    assert len(player_data_1) == 2
    assert player_data_1[0]['attributes']['game_id'] == '236'
    player_data_2 = results_data[1]['relationships']['players']['data']
    assert len(player_data_2) == 1
    assert player_data_2[0]['attributes']['game_id'] == '235'
    player_data_3 = results_data[2]['relationships']['players']['data']
    assert len(player_data_3) == 4
    assert player_data_3[0]['attributes']['game_id'] == '234'


def test_games_query_multiple_players(test_client, game_stats, game_player_stats, login, global_rating, maps):
    response = test_client.get('/games?filter[players]=testUser1,testUser3')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    results_data = result['data']
    assert len(results_data) == 1
    assert results_data[0]['id'] == '234'
    assert results_data[0]['relationships']['players']['data'][0]['attributes']['game_id'] == '234'


def test_games_query_player_no_result(test_client, game_stats, game_player_stats, login):
    response = test_client.get('/games?filter[players]=unknownUser')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    assert len(result['data']) == 0


def test_games_query_map_name(test_client, maps, game_player_stats, game_stats, global_rating, login):
    response = test_client.get('/games?filter[map_name]=testMap1')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    results_data = result['data']
    assert len(results_data) == 1
    assert results_data[0]['id'] == '234'
    assert results_data[0]['relationships']['players']['data'][0]['attributes']['game_id'] == '234'


def test_games_query_map_name_exclude(test_client, maps, game_player_stats, game_stats, global_rating, login):
    response = test_client.get('/games?filter[map_name]=testMap1&filter[map_exclude]=true')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    results_data = result['data']
    assert len(results_data) == 3
    assert results_data[0]['id'] == '237'
    player_data_1 = results_data[0]['relationships']['players']['data']
    assert len(player_data_1) == 2
    assert player_data_1[0]['attributes']['game_id'] == '237'


def test_games_query_map_exclude(test_client):
    response = test_client.get('/games?filter[map_exclude]=true')

    assert response.status_code == 422
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    assert 'errors' in result


def test_games_query_mod_name(test_client, maps, game_player_stats, game_stats, global_rating, login, mods):
    response = test_client.get('/games?filter[mod]=gfmod1')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    results_data = result['data']
    assert len(results_data) == 1
    assert results_data[0]['id'] == '234'
    assert results_data[0]['relationships']['players']['data'][0]['attributes']['game_id'] == '234'


def test_games_query_mod_name_no_result(test_client, maps, game_player_stats, game_stats, global_rating, login, mods):
    response = test_client.get('/games?filter[mod]=NoMod')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    results_data = result['data']
    assert len(results_data) == 0


def test_games_query_mod_id(test_client, maps, game_player_stats, game_stats, global_rating, login, mods):
    response = test_client.get('/games?filter[mod]=1')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    results_data = result['data']
    assert len(results_data) == 1
    assert results_data[0]['id'] == '234'
    assert results_data[0]['relationships']['players']['data'][0]['attributes']['game_id'] == '234'


def test_games_query_min_date_bounds(test_client, maps, game_player_stats, game_stats, global_rating, login, mods):
    response = test_client.get('/games?filter[min_datetime]=1997-07-17T19:20')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    results_data = result['data']
    assert len(results_data) == 3
    assert results_data[0]['id'] == '237'
    assert results_data[0]['relationships']['players']['data'][0]['attributes']['game_id'] == '237'
    assert results_data[1]['id'] == '236'
    assert results_data[1]['relationships']['players']['data'][0]['attributes']['game_id'] == '236'
    assert results_data[2]['id'] == '235'
    assert results_data[2]['relationships']['players']['data'][0]['attributes']['game_id'] == '235'


def test_games_query_max_date_bounds(test_client, maps, game_player_stats, game_stats, global_rating, login, mods):
    response = test_client.get('/games?filter[max_datetime]=1997-07-19T19:20')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    results_data = result['data']
    assert len(results_data) == 2
    assert results_data[0]['id'] == '235'
    assert results_data[0]['relationships']['players']['data'][0]['attributes']['game_id'] == '235'
    assert results_data[1]['id'] == '234'
    assert results_data[1]['relationships']['players']['data'][0]['attributes']['game_id'] == '234'


def test_games_query_max_date_depend_on_start_time(test_client, maps, game_player_stats, game_stats, global_rating, login, mods):
    response = test_client.get('/games?filter[max_datetime]=1997-07-16T19:20')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    results_data = result['data']
    assert len(results_data) == 1
    assert results_data[0]['id'] == '234'
    assert results_data[0]['relationships']['players']['data'][0]['attributes']['game_id'] == '234'


def test_games_query_malformed_min_date_bounds(test_client, maps, game_player_stats, game_stats, global_rating, login, mods):
    response = test_client.get('/games?filter[min_datetime]=asfd')

    assert response.status_code == 400
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    assert 'message' in result


def test_games_query_max_rating(test_client, game_stats, game_player_stats, global_rating, login, maps):
    response = test_client.get('/games?filter[max_rating]=1000')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    results_data = result['data']
    assert len(results_data) == 1
    assert results_data[0]['id'] == '237'
    player_data = results_data[0]['relationships']['players']['data']
    assert len(player_data) == 2
    assert player_data[0]['attributes']['game_id'] == '237'


def test_games_query_min_rating(test_client, game_stats, game_player_stats, global_rating, login, maps):
    response = test_client.get('/games?filter[min_rating]=1100')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    results_data = result['data']
    assert len(results_data) == 2
    assert results_data[0]['id'] == '236'
    assert results_data[0]['relationships']['players']['data'][0]['attributes']['game_id'] == '236'
    assert results_data[1]['id'] == '235'
    assert results_data[1]['relationships']['players']['data'][0]['attributes']['game_id'] == '235'


def test_games_query_max_and_min_rating(test_client, game_stats, game_player_stats, global_rating, login, maps):
    response = test_client.get('/games?filter[max_rating]=2000&filter[min_rating]=500')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    results_data = result['data']
    assert len(results_data) == 2
    assert results_data[0]['id'] == '237'
    assert results_data[0]['relationships']['players']['data'][0]['attributes']['game_id'] == '237'
    assert results_data[1]['id'] == '235'
    assert results_data[1]['relationships']['players']['data'][0]['attributes']['game_id'] == '235'


def test_games_query_rating_type_ladder(test_client, game_stats, game_player_stats, ladder, login, maps, mods):
    response = test_client.get('/games?filter[rating_type]=ladder')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    results_data = result['data']
    assert len(results_data) == 4
    assert results_data[0]['id'] == '237'
    assert results_data[0]['relationships']['players']['data'][0]['attributes']['game_id'] == '237'
    assert results_data[1]['id'] == '236'
    assert results_data[1]['relationships']['players']['data'][0]['attributes']['game_id'] == '236'
    assert results_data[2]['id'] == '235'
    assert results_data[2]['relationships']['players']['data'][0]['attributes']['game_id'] == '235'
    assert results_data[3]['id'] == '234'
    assert results_data[3]['relationships']['players']['data'][0]['attributes']['game_id'] == '234'


def test_games_query_min_and_max_rating_ladder(test_client, game_stats, game_player_stats, ladder, login, maps):
    response = test_client.get('/games?filter[max_rating]=2000&filter[min_rating]=500&filter[rating_type]=ladder')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    results_data = result['data']
    assert len(results_data) == 4
    assert results_data[0]['id'] == '237'
    assert results_data[1]['id'] == '236'
    assert results_data[2]['id'] == '235'
    assert results_data[3]['id'] == '234'
    assert results_data[0]['relationships']['players']['data'][0]['attributes']['game_id'] == '237'
    assert results_data[1]['relationships']['players']['data'][0]['attributes']['game_id'] == '236'
    assert results_data[2]['relationships']['players']['data'][0]['attributes']['game_id'] == '235'
    assert results_data[3]['relationships']['players']['data'][0]['attributes']['game_id'] == '234'


def test_games_query_victory_condition(test_client, game_stats, game_player_stats, global_rating, login, maps):
    response = test_client.get('/games?filter[victory_condition]=domination')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    results_data = result['data']
    assert len(results_data) == 1
    assert results_data[0]['id'] == '234'
    assert results_data[0]['relationships']['players']['data'][0]['attributes']['game_id'] == '234'


def test_games_malformed_query_victory_condition(test_client):
    response = test_client.get('/games?filter[victory_condition]=test')

    assert response.status_code == 400
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    assert 'message' in result


def test_games_query_max_player_count(test_client, maps, game_stats, game_player_stats, login, global_rating, app):
    app.debug = True
    response = test_client.get('/games?filter[max_player_count]=2')
    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    results_data = result['data']
    assert len(results_data) == 3


def test_games_query_min_player_count(test_client, maps, game_stats, game_player_stats, login, global_rating):
    response = test_client.get('/games?filter[min_player_count]=4')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    results_data = result['data']
    assert len(results_data) == 1


def test_games_query_all_parameters(test_client, maps, game_stats, game_player_stats, ladder, login):
    response = test_client.get('/games?filter[players]=testUser1,testUser3&filter[map_name]=testMap2'
                               '&filter[max_rating]=2000&filter[min_rating]=500&filter[game_type]=1'
                               '&filter[rating_type]=ladder&filter[map_exclude]=true&filter[max_player_count]=4'
                               '&filter[min_player_count]=3&filter[mod]=gfmod1&filter[min_datetime]=1997-07-16T19:20'
                               '&filter[max_datetime]=1997-07-25T19:20')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    results_data = result['data'][0]
    assert 'data' in result
    assert len(result['data'])
    player_data = results_data['relationships']['players']['data']
    assert len(player_data) == 4
    assert results_data['id'] == '234'
    assert results_data['attributes']['game_name'] == testGameName
    assert results_data['attributes']['validity'] == 'TOO_MANY_DESYNCS'
    assert results_data['attributes']['victory_condition'] == 'DOMINATION'
    assert player_data[0]['attributes']['game_id'] == '234'
    assert 'testUser' in player_data[0]['attributes']['login']


def test_game_id_one_player(test_client, game_stats, game_player_stats, global_rating, login, maps):
    response = test_client.get('/games/235')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    results_data = result['data'][0]
    assert 'data' in result
    assert results_data['id'] == '235'
    assert results_data['attributes']['game_name'] == testGame2Name
    assert results_data['attributes']['validity'] == 'TOO_MANY_DESYNCS'
    assert results_data['attributes']['victory_condition'] == 'ERADICATION'
    player_data = results_data['relationships']['players']['data']
    assert len(player_data) == 1


def test_game_id_four_players(test_client, game_stats, game_player_stats, global_rating, login, maps, mods):
    response = test_client.get('/games/234')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    result_data = result['data'][0]
    assert len(result_data['relationships']['players']['data']) == 4
    assert result_data['id'] == '234'
    assert result_data['attributes']['game_name'] == testGameName

    for item in result_data['relationships']['players']['data']:
        assert 'id' in item
        assert 'type' in item
        assert item['type'] == 'game_player_stats'


def test_game_id_no_game(test_client, game_stats, game_player_stats):
    response = test_client.get('/games/0')

    assert response.status_code == 404
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    assert 'errors' in result


def test_games_page_size(test_client, game_stats, game_player_stats, maps, mods, global_rating, login):
    response = test_client.get('/games?page[size]=1')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 1
    assert result['data'][0]['attributes']['game_name'] == testGame4Name


def test_games_invalid_page_size(test_client, game_stats):
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
