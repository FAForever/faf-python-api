import json

import pytest
from faf.api import Ranked1v1Schema

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

    def finalizer():
        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute("TRUNCATE TABLE ladder1v1_rating")

    request.addfinalizer(finalizer)


def test_rating_1v1(test_client, rating_ratings):
    response = test_client.get('/rating/1v1')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 4

    for item in result['data']:
        assert 'type' in item


def test_rating_global(test_client, rating_ratings):
    response = test_client.get('/rating/1v1/4')
    schema = Ranked1v1Schema()

    result, errors = schema.loads(response.data.decode('utf-8'))

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'
    assert not errors
    assert result['login'] == 'd'
    assert result['ranking'] == 1


def test_rating_not_found(test_client, rating_ratings):
    response = test_client.get('/rating/1v1/999')

    assert response.status_code == 404
    assert response.content_type == 'application/vnd.api+json'

    data = json.loads(response.data.decode('utf-8'))

    assert 'errors' in data


def test_rating_page_size(test_client, rating_ratings):
    response = test_client.get('/rating/1v1?page[size]=1')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 1


def test_rating_invalid_page_size(test_client, rating_ratings):
    response = test_client.get('/rating/1v1?page[size]=5001')

    result = json.loads(response.data.decode('utf-8'))

    assert response.status_code == 400
    assert result['errors'][0]['code'] == ErrorCode.QUERY_INVALID_PAGE_SIZE.value['code']
    assert result['errors'][0]['meta']['args'] == [5001]


def test_rating_page(test_client, rating_ratings):
    response = test_client.get('/rating/1v1?page[size]=1&page[number]=2')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 1
    assert result['data'][0]['attributes']['login'] == 'b'
    assert result['data'][0]['attributes']['ranking'] == 2


def test_rating_invalid_page(test_client):
    response = test_client.get('/rating/1v1?page[number]=-1')

    result = json.loads(response.data.decode('utf-8'))

    assert response.status_code == 400
    assert result['errors'][0]['code'] == ErrorCode.QUERY_INVALID_PAGE_NUMBER.value['code']
    assert result['errors'][0]['meta']['args'] == [-1]


def test_rating_sort_disallowed(test_client):
    response = test_client.get('/rating/1v1?sort=mean')

    result = json.loads(response.data.decode('utf-8'))

    assert response.status_code == 400
    assert result['errors'][0]['code'] == ErrorCode.QUERY_INVALID_SORT_FIELD.value['code']
    assert result['errors'][0]['meta']['args'] == ['mean']


def test_rating_filter_active(test_client, rating_ratings):
    response = test_client.get('/rating/1v1?filter[is_active]=true')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 3

    for item in result['data']:
        assert item['attributes']['is_active'] == True


def test_rating_filter_inactive(test_client, rating_ratings):
    response = test_client.get('/rating/1v1?filter[is_active]=false')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 1
    assert result['data'][0]['attributes']['is_active'] == 0


def test_rating_filter_player(test_client, rating_ratings):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("""UPDATE login SET login="test" WHERE login = 'a';""")

    response = test_client.get('/rating/1v1?filter[player]=te')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 1

    for item in result['data']:
        assert item['attributes']['login'] == 'test'

    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("""UPDATE login SET login="a" WHERE login = 'test';""")


def test_rating_1v1_stats(test_client, rating_ratings):
    response = test_client.get('/rating/1v1/stats')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert result['data']['attributes']['rating_distribution'] == {'1200': 1, '1400': 2}


def test_rating_global_stats(test_client, rating_ratings):
    response = test_client.get('/rating/global/stats')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert result['data']['attributes']['rating_distribution'] == {'1000': 1, '1600': 1}


def test_rating_invalid(test_client, rating_ratings):
    response = test_client.get('/rating/')

    assert response.status_code == 404


def test_rating_get_player_invalid(test_client, rating_ratings):
    response = test_client.get('/rating/lol/1')

    result = json.loads(response.data.decode('utf-8'))

    assert response.status_code == 400
    assert result['errors'][0]['detail'] == 'Rating type is not valid: lol. Please pick 1v1 or global.'
    assert result['errors'][0]['title'] == ErrorCode.QUERY_INVALID_RATING_TYPE.value['title']
    assert result['errors'][0]['meta']['args'] == ['lol']


def test_rating_get_player_1v1(test_client, rating_ratings):
    response = test_client.get('/rating/1v1/1')

    schema = Ranked1v1Schema()

    result, errors = schema.loads(response.data.decode('utf-8'))

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'
    assert not errors
    assert result['login'] == 'a'
    assert result['ranking'] == 1


def test_rating_get_player_global(test_client, rating_ratings):
    response = test_client.get('/rating/global/1')

    schema = Ranked1v1Schema()

    result, errors = schema.loads(response.data.decode('utf-8'))

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'
    assert not errors
    assert result['login'] == 'a'
    assert result['ranking'] == 2