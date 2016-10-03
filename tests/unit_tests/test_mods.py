import importlib
import json
import os
from io import BytesIO
from unittest.mock import Mock

import datetime
import marshmallow
import pytest
import sys

from pymysql.cursors import DictCursor

import api
from api import User
from api.error import ErrorCode
from faf import db
from faf.api import ModSchema


@pytest.fixture
def mods(request):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("DELETE FROM mod_stats")
        cursor.execute("DELETE FROM mod_version")
        cursor.execute("""DELETE FROM mod_stats""")
        cursor.execute("""DELETE FROM mod_version""")
        cursor.execute("DELETE FROM login")
        # TODO use common fixtures
        cursor.execute("""insert into login (id, login, password, email)
            values (1, 'User 1', '', 'user1@example.com')""")
        cursor.execute("""DELETE FROM `mod`""")
        cursor.execute("""insert into `mod` (id, display_name, author)
            VALUES (1, 'test-mod', 'baz'),
                   (2, 'test-mod2', 'baz'),
                   (3, 'test-mod3', 'baz')""")
        cursor.execute("""insert into mod_version (mod_id, uid, version, description, type, filename, icon) VALUES
                    (1, 'foo', 1, '', 'UI', 'foobar.zip', null),
                    (1, 'bar', 2, '', 'SIM', 'foobar2.zip', 'foobar.png'),
                    (2, 'baz', 1, '', 'UI', 'foobar3.zip', 'foobar3.png'),
                    (3, 'EA040F8E-857A-4566-9879-0D37420A5B9D', 1, '', 'SIM', 'foobar4.zip', 'foobar4.png')""")
        cursor.execute("""insert into mod_stats (mod_id, times_played, likes) VALUES
                    (1, 0, 3),
                    (2, 0, 4),
                    (3, 1, 5)""")


@pytest.fixture
def oauth():
    def get_token(access_token=None, refresh_token=None):
        return Mock(
            user=User(id=1),
            expires=datetime.datetime.now() + datetime.timedelta(hours=1),
            scopes=['read_achievements', 'write_achievements', 'upload_mod']
        )

    importlib.reload(api)
    importlib.reload(api.oauth_handlers)
    importlib.reload(api.mods)

    api.app.config.from_object('config')
    api.api_init()
    api.app.debug = True

    api.oauth.tokengetter(get_token)

    return api.app.test_client()


@pytest.fixture
def upload_dir(tmpdir, app):
    upload_dir = tmpdir.mkdir("mod_upload")
    app.config['MOD_UPLOAD_PATH'] = upload_dir.strpath
    return upload_dir


@pytest.fixture
def thumbnail_dir(tmpdir, app):
    thumbnail_dir = tmpdir.mkdir("mod_thumbnails")
    app.config['MOD_THUMBNAIL_PATH'] = thumbnail_dir.strpath
    return thumbnail_dir


def test_mods(test_client, mods):
    response = test_client.get('/mods')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 4

    for item in result['data']:
        assert 'type' in item


def test_mods_fields(test_client, mods):
    response = test_client.get('/mods?fields[mod]=name')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 4
    assert len(result['data'][0]['attributes']) == 1

    for item in result['data']:
        assert 'name' in item['attributes']
        assert 'version' not in item['attributes']
        assert 'author' not in item['attributes']


def test_mods_fields_two(test_client, mods):
    response = test_client.get('/mods?fields[mod]=name,author')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 4
    assert len(result['data'][0]['attributes']) == 2

    for item in result['data']:
        assert 'name' in item['attributes']
        assert 'author' in item['attributes']
        assert 'version' not in item['attributes']


def test_mod(test_client, mods):
    response = test_client.get('/mods/EA040F8E-857A-4566-9879-0D37420A5B9D')
    schema = ModSchema()

    result, errors = schema.loads(response.data.decode('utf-8'))

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'
    assert not errors
    assert result['author'] == 'baz'


def test_mod_not_found(test_client, mods):
    response = test_client.get('/mods/i_do_not_exist')

    assert response.status_code == 404
    assert response.content_type == 'application/vnd.api+json'

    data = json.loads(response.data.decode('utf-8'))

    assert 'errors' in data


def test_mods_page_size(test_client, mods):
    response = test_client.get('/mods?page[size]=1')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 1


def test_mods_invalid_page_size(test_client, mods):
    response = test_client.get('/mods?page[size]=1001')

    result = json.loads(response.data.decode('utf-8'))

    assert response.status_code == 400
    assert result['errors'][0]['code'] == ErrorCode.QUERY_INVALID_PAGE_SIZE.value['code']
    assert result['errors'][0]['meta']['args'] == [1001]


def test_mods_page(test_client, mods):
    response = test_client.get('/mods?page[size]=1&page[number]=2')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 1
    assert result['data'][0]['attributes']['name'] == 'test-mod'


def test_mods_invalid_page(test_client, mods):
    response = test_client.get('/mods?page[number]=-1')

    result = json.loads(response.data.decode('utf-8'))

    assert response.status_code == 400
    assert result['errors'][0]['code'] == ErrorCode.QUERY_INVALID_PAGE_NUMBER.value['code']
    assert result['errors'][0]['meta']['args'] == [-1]


def test_mods_download_url(test_client, mods):
    response = test_client.get('/mods?sort=name')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['data']) > 0

    mod = result['data']
    assert mod[0]['attributes']['download_url'] == 'http://content.faforever.com/faf/vault/foobar.zip'
    assert mod[1]['attributes']['download_url'] == 'http://content.faforever.com/faf/vault/foobar2.zip'
    assert mod[2]['attributes']['download_url'] == 'http://content.faforever.com/faf/vault/foobar3.zip'


def test_mods_thumbnail_url(test_client, mods):
    response = test_client.get('/mods?sort=name')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['data']) > 0

    mod = result['data']
    assert 'thumbnail_url' not in mod[0]['attributes']
    assert mod[1]['attributes']['thumbnail_url'] == 'http://content.faforever.com/faf/vault/mods_thumbs/foobar.png'
    assert mod[2]['attributes']['thumbnail_url'] == 'http://content.faforever.com/faf/vault/mods_thumbs/foobar3.png'


def test_mods_sort_by_create_time(test_client, mods):
    response = test_client.get('/mods?sort=create_time')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['data']) > 0

    previous_create_time = marshmallow.utils.from_iso('1970-01-01T00:00:00+00:00')
    for item in result['data']:
        new_date = marshmallow.utils.from_iso(item['attributes']['create_time'])
        assert new_date >= previous_create_time
        previous_create_time = new_date


def test_mods_sort_by_likes(test_client, mods):
    response = test_client.get('/mods?sort=likes')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['data']) > 0

    previous_likes = -1
    for item in result['data']:
        assert item['attributes']['likes'] >= previous_likes
        previous_likes = item['attributes']['likes']


def test_mods_sort_by_likes_desc(test_client, mods):
    response = test_client.get('/mods?sort=-likes')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['data']) > 0

    previous_likes = sys.maxsize
    for item in result['data']:
        assert item['attributes']['likes'] <= previous_likes
        previous_likes = item['attributes']['likes']


def test_mods_inject_sql_order(test_client):
    response = test_client.get("/mods?sort=' or%201=1; --")

    result = json.loads(response.data.decode('utf-8'))

    assert response.status_code == 400
    assert result['errors'][0]['code'] == ErrorCode.QUERY_INVALID_SORT_FIELD.value['code']
    assert result['errors'][0]['meta']['args'] == ["' or 1=1; --"]


def test_mods_upload_no_file_results_400(oauth, app, tmpdir):
    response = oauth.post('/mods/upload')

    assert response.status_code == 400
    result = json.loads(response.get_data(as_text=True))
    assert len(result['errors']) == 1
    assert result['errors'][0]['code'] == ErrorCode.UPLOAD_FILE_MISSING.value['code']


def test_mods_upload_txt_results_400(oauth, app, tmpdir):
    response = oauth.post('/mods/upload', data={'file': (BytesIO('1'.encode('utf-8')), 'mod_name.txt'),
                                                'metadata': json.dumps(dict(is_ranked=True))})

    assert response.status_code == 400
    result = json.loads(response.get_data(as_text=True))
    assert len(result['errors']) == 1
    assert result['errors'][0]['code'] == ErrorCode.UPLOAD_INVALID_FILE_EXTENSION.value['code']


def test_mods_upload_is_metadata_missing(oauth, app, tmpdir):
    upload_dir = tmpdir.mkdir("mod_upload")
    app.config['MOD_UPLOAD_PATH'] = upload_dir.strpath
    response = oauth.post('/mods/upload',
                          data={'file': (BytesIO('my file contents'.encode('utf-8')), 'mod_name.zip')})

    assert response.status_code == 400
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.get_data(as_text=True))
    assert len(result['errors']) == 1
    assert result['errors'][0]['code'] == ErrorCode.UPLOAD_METADATA_MISSING.value['code']


@pytest.mark.parametrize("ranked", [True, False])
def test_mod_upload(oauth, ranked, mods, upload_dir, thumbnail_dir):
    mod_zip = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../data/No Friendly Fire.zip')
    with open(mod_zip, 'rb') as file:
        response = oauth.post('/mods/upload',
                              data={'file': (file, os.path.basename(mod_zip)),
                                    'metadata': json.dumps(dict(is_ranked=ranked))})

    assert response.status_code == 200
    assert 'ok' == response.get_data(as_text=True)
    assert os.path.isfile(upload_dir.join(os.path.basename('no_friendly_fire.v0003.zip')).strpath)
    assert os.path.isfile(thumbnail_dir.join('no_friendly_fire.v0003.png').strpath)

    with db.connection:
        cursor = db.connection.cursor(DictCursor)
        cursor.execute("SELECT id, display_name, author, uploader from `mod` WHERE display_name = 'No Friendly Fire'")
        result = cursor.fetchone()

        assert result['display_name'] == 'No Friendly Fire'
        assert result['author'] == 'IceDreamer'
        assert result['uploader'] == 1

        mod_id = result['id']

        cursor.execute("SELECT uid, type, description, version, filename, icon, ranked, hidden, mod_id "
                       "from mod_version WHERE uid = '26778D4E-BA75-5CC2-CBA8-63795BDE74AA'")
        result = cursor.fetchone()

        assert result['uid'] == '26778D4E-BA75-5CC2-CBA8-63795BDE74AA'
        assert result['type'] == 'SIM'
        assert result['description'] == 'All friendly fire, including between allies, is turned off.'
        assert result['version'] == 3
        assert result['filename'] == 'mods/no_friendly_fire.v0003.zip'
        assert result['icon'] == 'no_friendly_fire.v0003.png'
        assert result['ranked'] == (1 if ranked else 0)
        assert result['hidden'] == 0
        assert result['mod_id'] == mod_id
