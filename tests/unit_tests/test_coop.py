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
def maps(request):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("TRUNCATE TABLE coop_map")
        # TODO use common fixtures
        cursor.execute("""insert into coop_map (id, name, description, version, type, filename)
        values
        (1, 'SCMP 001', 'Description 1', 1, 1, 'maps/scmp_001.v0001.zip'),
        (2, 'SCMP 002', 'Description 2', 2, 1, 'maps/scmp_002.v0002.zip'),
        (3, 'SCMP 003', 'Description 3', 2, 1, 'maps/scmp_003.v0002.zip')""")

    def finalizer():
        with db.connection:
            cursor = db.connection.cursor()
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


def test_coop_missions(test_client, maps):
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


def test_coop_missions_fields(test_client, maps):
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


def test_coop_missions_fields_two(test_client, maps):
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


def test_coop_missions_page_size(test_client, maps):
    response = test_client.get('/coop/missions?page[size]=1')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 1


def test_coop_missions_invalid_page_size(test_client, maps):
    response = test_client.get('/coop/missions?page[size]=1001')

    assert response.status_code == 400
    result = json.loads(response.get_data(as_text=True))
    assert len(result['errors']) == 1
    assert result['errors'][0]['code'] == ErrorCode.QUERY_INVALID_PAGE_SIZE.value['code']


def test_coop_missions_page(test_client, maps):
    response = test_client.get('/coop/missions?page[size]=1&page[number]=2')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 1
    assert result['data'][0]['attributes']['name'] == 'SCMP 002'


def test_coop_missions_invalid_page(test_client, maps):
    response = test_client.get('/coop/missions?page[number]=-1')

    result = json.loads(response.data.decode('utf-8'))

    assert response.status_code == 400
    assert result['errors'][0]['code'] == ErrorCode.QUERY_INVALID_PAGE_NUMBER.value['code']
    assert result['errors'][0]['meta']['args'] == [-1]


def test_coop_missions_sort_by_version(test_client, maps):
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
