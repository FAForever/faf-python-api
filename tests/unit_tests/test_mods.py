import json
from io import BytesIO
from flask import Response


def test_get_mods(test_client):
    response = test_client.get('/mods')

    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    response = json.loads(response.data.decode())
    assert 'data' in response

    data = response['data']

    for item in data:
        assert 'type' in item


def test_mods_upload(test_client, app, tmpdir):
    upload_dir = tmpdir.mkdir("map_upload")
    app.config['MOD_UPLOAD_PATH'] = upload_dir.strpath
    response = test_client.post('/mods/upload',
                                data={'file': (BytesIO('my file contents'.encode('utf-8')), 'mod_name.zip')})

    assert response.status_code == 200
    assert 'ok' == response.get_data(as_text=True)

    with open(upload_dir.join('mod_name.zip').strpath, 'r') as file:
        assert file.read() == 'my file contents'


def test_mods_upload_no_file_results_400(test_client, app, tmpdir):
    response = test_client.post('/mods/upload')

    assert response.status_code == 400
    assert json.loads(response.get_data(as_text=True))['message'] == 'No file has been provided'


def test_mods_upload_txt_results_400(test_client, app, tmpdir):
    response = test_client.post('/mods/upload', data={'file': (BytesIO('1'.encode('utf-8')), 'mod_name.txt')})

    assert response.status_code == 400
    assert json.loads(response.get_data(as_text=True))['message'] == 'Invalid file extension'
