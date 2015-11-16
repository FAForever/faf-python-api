import json
from io import BytesIO

import pytest
import sys

from faf import db


@pytest.fixture
def maps(request, app):
    app.debug = True
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        cursor.execute("TRUNCATE TABLE table_map")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        cursor.execute("""INSERT INTO table_map
        (mapuid, max_players, name, hidden) VALUES
        (111, 4, 'a', 0),
        (222, 8, 'b', 0),
        (333, 12, 'c', 0)""")

    def finalizer():
        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            cursor.execute("TRUNCATE TABLE table_map")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

    request.addfinalizer(finalizer)


def test_maps(test_client, maps):
    response = test_client.get('/maps')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) > 0

    for item in result['data']:
        assert 'type' in item


def test_maps_max(test_client, maps):
    response = test_client.get('/maps?max=1')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 1


def test_maps_invalid_max(test_client, maps):
    response = test_client.get('/maps?max=101')

    assert response.status_code == 400
    assert json.loads(response.get_data(as_text=True))['message'] == 'Invalid max'


def test_maps_page(test_client, maps):
    response = test_client.get('/maps?max=1&page=2')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 1
    assert result['data'][0]['attributes']['name'] == 'b'


def test_maps_invalid_page(test_client, maps):
    response = test_client.get('/maps?page=-1')

    assert response.status_code == 400
    assert json.loads(response.get_data(as_text=True))['message'] == 'Invalid page'


def test_maps_sort_by_max_players(test_client, maps):
    response = test_client.get('/maps?order_column=max_players')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['data']) > 0

    previous_create_time = 0
    for item in result['data']:
        assert item['attributes']['max_players'] > previous_create_time
        previous_create_time = item['attributes']['max_players']


def test_maps_sort_by_max_players_desc(test_client, maps):
    response = test_client.get('/maps?order_column=max_players&order=desc')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['data']) > 0

    previous_create_time = sys.maxsize
    for item in result['data']:
        assert item['attributes']['max_players'] < previous_create_time
        previous_create_time = item['attributes']['max_players']


def test_maps_inject_sql_order(test_client):
    response = test_client.get('/maps?order=or%201=1')

    assert response.status_code == 400
    assert json.loads(response.get_data(as_text=True))['message'] == 'Invalid order'


def test_maps_inject_sql_order_column(test_client):
    response = test_client.get('/maps?order_column=or%201=1')

    assert response.status_code == 400
    assert json.loads(response.get_data(as_text=True))['message'] == 'Invalid order column'


def test_maps_upload(test_client, app, tmpdir):
    upload_dir = tmpdir.mkdir("map_upload")
    app.config['MAP_UPLOAD_PATH'] = upload_dir.strpath
    response = test_client.post('/maps/upload',
                                data={'file': (BytesIO('my file contents'.encode('utf-8')), 'map_name.zip')})

    assert response.status_code == 200
    assert 'ok' == response.get_data(as_text=True)

    with open(upload_dir.join('map_name.zip').strpath, 'r') as file:
        assert file.read() == 'my file contents'


def test_maps_upload_no_file_results_400(test_client, app, tmpdir):
    response = test_client.post('/maps/upload')

    assert response.status_code == 400
    assert json.loads(response.get_data(as_text=True))['message'] == 'No file has been provided'


def test_maps_upload_txt_results_400(test_client, app, tmpdir):
    response = test_client.post('/maps/upload', data={'file': (BytesIO('1'.encode('utf-8')), 'map_name.txt')})

    assert response.status_code == 400
    assert json.loads(response.get_data(as_text=True))['message'] == 'Invalid file extension'
