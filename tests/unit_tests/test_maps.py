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
from faf import db


@pytest.fixture
def maps(request):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute("TRUNCATE TABLE map_version")
        cursor.execute("TRUNCATE TABLE map")
        cursor.execute("DELETE FROM login")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        # TODO use common fixtures
        cursor.execute("""insert into login
        (id, login, password, email)
        values
        (1, 'User 1', '', 'user1@example.com'),
        (2, 'User 2', '', 'user2@example.com'),
        (3, 'User 3', '', 'user3@example.com')""")
        cursor.execute("""insert into map (id, display_name, map_type, battle_type, uploader)
        values
        (1, 'SCMP_001', 'FFA', 'skirmish', 1),
        (2, 'SCMP_002', 'FFA', 'skirmish', 2),
        (3, 'SCMP_003', 'FFA', 'skirmish', 2),
        (4, 'Map with space', 'FFA', 'skirmish', 3)""")
        cursor.execute("""insert into map_version
        (description, max_players, width, height, version, filename, hidden, map_id)
        values
        ('SCMP 001', 4, 5, 5, 1, 'maps/scmp_001.v0001.zip', 0, 1),
        ('SCMP 002', 6, 5, 5, 1, 'maps/scmp_002.v0001.zip', 0, 2),
        ('SCMP 003', 8, 5, 5, 1, 'maps/scmp_003.v0001.zip', 0, 3),
        ('Testing spaces', 8, 5, 5, 1, 'maps/map with space.zip', 0, 4)""")

    def finalizer():
        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            cursor.execute("TRUNCATE TABLE map_version")
            cursor.execute("TRUNCATE TABLE map")
            cursor.execute("DELETE FROM login")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

    request.addfinalizer(finalizer)


@pytest.fixture
def oauth():
    def get_token(access_token=None, refresh_token=None):
        return Mock(
            user=User(id=1),
            expires=datetime.datetime.now() + datetime.timedelta(hours=1),
            scopes=['read_achievements', 'write_achievements', 'upload_map']
        )

    importlib.reload(api)
    importlib.reload(api.oauth_handlers)
    importlib.reload(api.maps)

    api.app.config.from_object('config')
    api.api_init()
    api.app.debug = True

    api.oauth.tokengetter(get_token)

    return api.app.test_client()


def test_maps(test_client, maps):
    response = test_client.get('/maps')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) > 0

    for item in result['data']:
        assert 'type' in item
        assert 'author' in item['attributes']
        assert 'create_time' in item['attributes']
        assert 'thumbnail_url_small' in item['attributes']
        assert 'thumbnail_url_large' in item['attributes']


def test_maps_fields(test_client, maps):
    response = test_client.get('/maps?fields[map]=display_name')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 4
    assert len(result['data'][0]['attributes']) == 1

    for item in result['data']:
        assert 'display_name' in item['attributes']
        assert 'version' not in item['attributes']


def test_maps_fields_two(test_client, maps):
    response = test_client.get('/maps?fields[map]=display_name,max_players')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 4
    assert len(result['data'][0]['attributes']) == 2

    for item in result['data']:
        assert 'display_name' in item['attributes']
        assert 'max_players' in item['attributes']
        assert 'version' not in item['attributes']


def test_maps_page_size(test_client, maps):
    response = test_client.get('/maps?page[size]=1')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 1


def test_maps_invalid_page_size(test_client, maps):
    response = test_client.get('/maps?page[size]=1001')

    assert response.status_code == 400
    assert json.loads(response.get_data(as_text=True))['message'] == 'Invalid page size'


def test_maps_page(test_client, maps):
    response = test_client.get('/maps?page[size]=1&page[number]=2')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 1
    assert result['data'][0]['attributes']['display_name'] == 'SCMP_002'


def test_maps_invalid_page(test_client, maps):
    response = test_client.get('/maps?page[number]=-1')

    assert response.status_code == 400
    assert json.loads(response.get_data(as_text=True))['message'] == 'Invalid page number'


def test_maps_sort_by_max_players(test_client, maps):
    response = test_client.get('/maps?sort=max_players')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['data']) > 0

    previous_max_players = 0
    for item in result['data']:
        assert item['attributes']['max_players'] >= previous_max_players
        previous_max_players = item['attributes']['max_players']


def test_maps_sort_by_max_players_desc(test_client, maps):
    response = test_client.get('/maps?sort=-max_players')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['data']) > 0

    previous_max_players = sys.maxsize
    for item in result['data']:
        assert item['attributes']['max_players'] <= previous_max_players
        previous_max_players = item['attributes']['max_players']


def test_maps_inject_sql_sort(test_client):
    response = test_client.get('/maps?sort=or%201=1')

    assert response.status_code == 400
    assert json.loads(response.get_data(as_text=True))['message'] == 'Invalid sort field'


def test_maps_upload_is_metadata_missing(oauth, app, tmpdir):
    upload_dir = tmpdir.mkdir("map_upload")
    app.config['MAP_UPLOAD_PATH'] = upload_dir.strpath
    response = oauth.post('/maps/upload',
                          data={'file': (BytesIO('my file contents'.encode('utf-8')), 'map_name.zip')})

    assert response.status_code == 400
    assert response.content_type == 'application/vnd.api+json'

    assert json.loads(response.get_data(as_text=True))['message'] == "Value 'metadata' is missing"


def test_maps_upload_no_file_results_400(oauth, app, tmpdir):
    response = oauth.post('/maps/upload')

    assert response.status_code == 400
    assert json.loads(response.get_data(as_text=True))['message'] == 'No file has been provided'


def test_maps_upload_txt_results_400(oauth, app, tmpdir):
    response = oauth.post('/maps/upload', data={'file': (BytesIO('1'.encode('utf-8')), 'map_name.txt'),
                                                'metadata': json.dumps(dict(is_ranked=True))})

    assert response.status_code == 400
    assert json.loads(response.get_data(as_text=True))['message'] == 'Invalid file extension'


def test_map_by_name(test_client, app, maps):
    response = test_client.get('/maps?filter%5Btechnical_name%5D=scmp_002.v0001')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert result['data']['id'] == '2'
    assert result['data']['attributes']['author'] == 'User 2'
    assert result['data']['attributes']['display_name'] == 'SCMP_002'
    assert result['data']['attributes'][
               'download_url'] == 'http://content.faforever.com/faf/vault/maps/scmp_002.v0001.zip'
    assert result['data']['attributes']['thumbnail_url_small'] == 'http://content.faforever.com/faf/vault' \
                                                                  '/map_previews/small/scmp_002.v0001.png'
    assert result['data']['attributes']['thumbnail_url_large'] == 'http://content.faforever.com/faf/vault' \
                                                                  '/map_previews/large/scmp_002.v0001.png'


@pytest.mark.parametrize("ranked", [True, False])
def test_map_upload(oauth, app, maps, tmpdir, ranked):
    upload_dir = tmpdir.mkdir("map_upload")
    small_preview_dir = tmpdir.mkdir("small_previews")
    large_preview_dir = tmpdir.mkdir("large_previews")

    app.config['MAP_UPLOAD_PATH'] = upload_dir.strpath
    app.config['SMALL_PREVIEW_UPLOAD_PATH'] = small_preview_dir.strpath
    app.config['LARGE_PREVIEW_UPLOAD_PATH'] = large_preview_dir.strpath

    map_zip = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../data/scmp_037.zip')
    with open(map_zip, 'rb') as file:
        response = oauth.post('/maps/upload',
                              data={'file': (file, os.path.basename(map_zip)),
                                    'metadata': json.dumps(dict(is_ranked=ranked))})

    assert response.status_code == 200, json.loads(response.get_data(as_text=True))['message']
    assert 'ok' == response.get_data(as_text=True)
    assert os.path.isfile(upload_dir.join(os.path.basename('scmp_037.v0003.zip')).strpath)
    assert os.path.isfile(small_preview_dir.join('scmp_037.v0003.png').strpath)
    assert os.path.isfile(large_preview_dir.join('scmp_037.v0003.png').strpath)

    with db.connection:
        cursor = db.connection.cursor(DictCursor)
        cursor.execute("SELECT display_name, map_type, battle_type, ranked, uploader from map WHERE id = 5")
        result = cursor.fetchone()

        assert result['display_name'] == 'Sludge'
        assert result['map_type'] == 'skirmish'
        assert result['battle_type'] == 'FFA'
        assert result['ranked'] == (1 if ranked else 0)
        assert result['uploader'] == 1
