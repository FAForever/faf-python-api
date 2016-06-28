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
        (mapuid, max_players, name, filename, hidden) VALUES
        (111, 4, 'a', 'maps/a.v0001.zip', 0),
        (222, 8, 'b', 'maps/b.v0001.zip', 0),
        (333, 12, 'c', 'maps/c.v0001.zip', 0)""")

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


def test_maps_fields(test_client, maps):
    response = test_client.get('/maps?fields[map]=display_name')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 3
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
    assert len(result['data']) == 3
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
    assert result['data'][0]['attributes']['display_name'] == 'b'


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

    previous_create_time = 0
    for item in result['data']:
        assert item['attributes']['max_players'] > previous_create_time
        previous_create_time = item['attributes']['max_players']


def test_maps_sort_by_max_players_desc(test_client, maps):
    response = test_client.get('/maps?sort=-max_players')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['data']) > 0

    previous_create_time = sys.maxsize
    for item in result['data']:
        assert item['attributes']['max_players'] < previous_create_time
        previous_create_time = item['attributes']['max_players']


def test_maps_inject_sql_sort(test_client):
    response = test_client.get('/maps?sort=or%201=1')

    assert response.status_code == 400
    assert json.loads(response.get_data(as_text=True))['message'] == 'Invalid sort field'


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


def test_map_by_name(test_client, app, maps):
    response = test_client.get('/maps?filter%5Btechnical_name%5D=b.v0001')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert result['data']['id'] == '222'
    assert result['data']['attributes']['display_name'] == 'b'
    assert result['data']['attributes']['download_url'] == 'http://content.faforever.com/faf/vault/maps/b.v0001.zip'
    assert result['data']['attributes']['thumbnail_url_small'] == 'http://content.faforever.com/faf/vault' \
                                                                  '/map_previews/small/maps/b.v0001.zip'
    assert result['data']['attributes']['thumbnail_url_large'] == 'http://content.faforever.com/faf/vault' \
                                                                  '/map_previews/large/maps/b.v0001.zip'
