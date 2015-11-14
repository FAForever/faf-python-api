import json
from io import BytesIO


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
