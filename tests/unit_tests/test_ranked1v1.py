import json

import pytest
from faf.api import Ranked1v1Schema

from faf import db


@pytest.fixture
def ranked1v1_ratings(request, app):
    app.debug = True
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("TRUNCATE TABLE ladder1v1_rating")
        cursor.execute("TRUNCATE TABLE login")
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
        (4, 1500, 100, 30, 17, 1)""")

    def finalizer():
        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute("TRUNCATE TABLE ladder1v1_rating")

    request.addfinalizer(finalizer)


def test_ranked1v1(test_client, ranked1v1_ratings):
    response = test_client.get('/ranked1v1')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 4

    for item in result['data']:
        assert 'type' in item


def test_ranked1v1(test_client, ranked1v1_ratings):
    response = test_client.get('/ranked1v1/2')
    schema = Ranked1v1Schema()

    result, errors = schema.loads(response.data.decode('utf-8'))

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'
    assert not errors
    assert result['login'] == 'b'
    assert result['ranking'] == 2


def test_ranked1v1_not_found(test_client, ranked1v1_ratings):
    response = test_client.get('/ranked1v1/999')

    assert response.status_code == 404
    assert response.content_type == 'application/vnd.api+json'

    data = json.loads(response.data.decode('utf-8'))

    assert 'errors' in data


def test_ranked1v1_page_size(test_client, ranked1v1_ratings):
    response = test_client.get('/ranked1v1?page[size]=1')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 1


def test_ranked1v1_invalid_page_size(test_client, ranked1v1_ratings):
    response = test_client.get('/ranked1v1?page[size]=5001')

    assert response.status_code == 400
    assert json.loads(response.get_data(as_text=True))['message'] == 'Invalid page size'


def test_ranked1v1_page(test_client, ranked1v1_ratings):
    response = test_client.get('/ranked1v1?page[size]=1&page[number]=2')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 1
    assert result['data'][0]['attributes']['login'] == 'b'
    assert result['data'][0]['attributes']['ranking'] == 2


def test_ranked1v1_invalid_page(test_client):
    response = test_client.get('/ranked1v1?page[number]=-1')

    assert response.status_code == 400
    assert json.loads(response.get_data(as_text=True))['message'] == 'Invalid page number'


def test_ranked1v1_sort_disallowed(test_client):
    response = test_client.get('/ranked1v1?sort=mean')

    assert response.status_code == 400
    assert json.loads(response.get_data(as_text=True))['message'] == 'Sorting is not supported for ranked1v1'


def test_ranked1v1_filter_active(test_client, ranked1v1_ratings):
    response = test_client.get('/ranked1v1?filter[is_active]=true')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 3

    for item in result['data']:
        assert item['attributes']['is_active'] == True


def test_ranked1v1_filter_inactive(test_client, ranked1v1_ratings):
    response = test_client.get('/ranked1v1?filter[is_active]=false')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 1
    assert result['data'][0]['attributes']['is_active'] == 0


def test_ranked1v1_stats(test_client, ranked1v1_ratings):
    response = test_client.get('/ranked1v1/stats')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert result['data']['attributes']['rating_distribution'] == {'1200': 1, '1400': 2}
