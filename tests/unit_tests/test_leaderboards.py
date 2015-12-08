import json
import sys

import pytest
from faf.api import LeaderboardSchema

from faf import db


@pytest.fixture
def leaderboards(request, app):
    app.debug = True
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("TRUNCATE TABLE ladder1v1_rating")
        cursor.execute("TRUNCATE TABLE login")
        cursor.execute("""INSERT INTO login
        (id, login, password, email) VALUES
        (1, 'a', '', 'a'),
        (2, 'b', '', 'b'),
        (3, 'c', '', 'c')""")
        cursor.execute("""INSERT INTO ladder1v1_rating
        (id, mean, deviation, numGames, winGames, is_active) VALUES
        (1, 1000, 300, 10, 5, 0),
        (2, 2000, 200, 20, 9, 1),
        (3, 1500, 100, 30, 17, 1)""")

    def finalizer():
        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute("TRUNCATE TABLE ladder1v1_rating")

    request.addfinalizer(finalizer)


def test_leaderboards(test_client, leaderboards):
    response = test_client.get('/leaderboards')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 3

    for item in result['data']:
        assert 'type' in item


def test_leaderboard(test_client, leaderboards):
    response = test_client.get('/leaderboards/3')
    schema = LeaderboardSchema()

    result, errors = schema.loads(response.data.decode('utf-8'))

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'
    assert not errors
    assert result['login'] == 'c'
    assert result['ranking'] == 2


def test_leaderboard_not_found(test_client, leaderboards):
    response = test_client.get('/leaderboards/4')

    assert response.status_code == 404
    assert response.content_type == 'application/vnd.api+json'

    data = json.loads(response.data.decode('utf-8'))

    assert 'errors' in data


def test_leaderboards_page_size(test_client, leaderboards):
    response = test_client.get('/leaderboards?page[size]=1')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 1


def test_leaderboards_invalid_page_size(test_client, leaderboards):
    response = test_client.get('/leaderboards?page[size]=1001')

    assert response.status_code == 400
    assert json.loads(response.get_data(as_text=True))['message'] == 'Invalid page size'


def test_leaderboards_page(test_client, leaderboards):
    response = test_client.get('/leaderboards?page[size]=1&page[number]=2')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 1
    assert result['data'][0]['attributes']['login'] == 'b'
    assert result['data'][0]['attributes']['ranking'] == 2


def test_leaderboards_invalid_page(test_client):
    response = test_client.get('/leaderboards?page[number]=-1')

    assert response.status_code == 400
    assert json.loads(response.get_data(as_text=True))['message'] == 'Invalid page number'


def test_leaderboards_sort_disallowed(test_client):
    response = test_client.get('/leaderboards?sort=mean')

    assert response.status_code == 400
    assert json.loads(response.get_data(as_text=True))['message'] == 'Sorting is not supported for leaderboards'

