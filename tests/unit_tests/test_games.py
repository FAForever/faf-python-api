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
        (234, now(), 'faf', 2, 146315, 5092, 'testGame', 1),
        (235, now(), 'faf', 2, 146315, 5092, 'testGame2', 1)""")

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
        (146315, 234, 146315, 0, 1, 1, 1, 1, 1, 1, 2, 2, 50, now()),
        (146316, 234, 146316, 0, 1, 1, 1, 1, 1, 1, 2, 2, 50, now()),
        (146317, 234, 146317, 0, 1, 1, 1, 1, 1, 1, 2, 2, 50, now()),
        (146318, 234, 146318, 0, 1, 1, 1, 1, 1, 1, 2, 2, 50, now())""")

    def finalizer():
        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute("TRUNCATE TABLE game_player_stats")

    request.addfinalizer(finalizer)


def test_games(test_client, games):
    response = test_client.get('/games')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 2

    for item in result['data']:
        assert 'id' in item
        assert 'type' in item
        assert item['type'] == 'game_stats'


def test_games_no_games(test_client):
    response = test_client.get('/games')

    assert response.status_code == 404
    assert response.content_type == 'application/vnd.api+json'

    data = json.loads(response.data.decode('utf-8'))

    assert 'errors' in data


def test_game_id_no_players(test_client, games):
    response = test_client.get('/games/235')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['relationships']['players']['data']) == 0
    assert result['data']['id'] == '235'
    assert result['data']['attributes']['game_name'] == testGame2Name


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


def test_mods_invalid_page(test_client, games):
    response = test_client.get('/games?page[number]=-1')

    assert response.status_code == 400
    assert json.loads(response.get_data(as_text=True))['message'] == 'Invalid page number'

