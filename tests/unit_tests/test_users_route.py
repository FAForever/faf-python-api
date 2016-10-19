import json
import time

import pytest
from faf import db

from api.error import ErrorCode
from api.users_route import create_token


@pytest.fixture
def setup_users(request, app):
    app.debug = True
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("TRUNCATE TABLE ladder1v1_rating")
        cursor.execute("TRUNCATE TABLE global_rating")
        cursor.execute("delete from login")
        cursor.execute("""INSERT INTO login
        (id, login, password, email) VALUES
        (1, 'a', 'pw_a', 'a@aa.aa'),
        (2, 'b', 'pw_b', 'b@bb.bb')""")
        cursor.execute("TRUNCATE TABLE email_domain_blacklist")
        cursor.execute("INSERT INTO email_domain_blacklist VALUES ('zzz.com'), ('abc.de')")

    def finalizer():
        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute("TRUNCATE TABLE ladder1v1_rating")
            cursor.execute("TRUNCATE TABLE global_rating")

    request.addfinalizer(finalizer)


def test_register_invalid_email(test_client, setup_users):
    response = test_client.post('/users/register',
                                data={'name': 'a', 'email': 'abbb.cc', 'pw_hash': '0000'})

    assert response.status_code == 400
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['errors']) == 1
    assert result['errors'][0]['code'] == ErrorCode.REGISTRATION_INVALID_EMAIL.value['code']


def test_register_invalid_username(test_client, setup_users):
    response = test_client.post('/users/register',
                                data={'name': 'a,b', 'email': 'a@bbb.cc', 'pw_hash': '0000'})

    assert response.status_code == 400
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['errors']) == 1
    assert result['errors'][0]['code'] == ErrorCode.REGISTRATION_INVALID_USERNAME.value['code']


def test_register_username_taken(test_client, setup_users):
    response = test_client.post('/users/register',
                                data={'name': 'A', 'email': 'a@bbb.cc', 'pw_hash': '0000'})

    assert response.status_code == 400
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['errors']) == 1
    assert result['errors'][0]['code'] == ErrorCode.REGISTRATION_USERNAME_TAKEN.value['code']


def test_register_email_taken(test_client, setup_users):
    response = test_client.post('/users/register',
                                data={'name': 'abc', 'email': 'a@AA.aa', 'pw_hash': '0000'})

    assert response.status_code == 400
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['errors']) == 1
    assert result['errors'][0]['code'] == ErrorCode.REGISTRATION_EMAIL_REGISTERED.value['code']


def test_register_email_blacklisted(test_client, setup_users):
    response = test_client.post('/users/register',
                                data={'name': 'alpha', 'email': 'a@ZZZ.com', 'pw_hash': '0000'})

    assert response.status_code == 400
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['errors']) == 1
    assert result['errors'][0]['code'] == ErrorCode.REGISTRATION_BLACKLISTED_EMAIL.value['code']


def test_validate_registration_invalid_email(test_client, setup_users):
    response = test_client.get('/users/validate_registration/' + create_token('a', 'abbb.cc', '0000', 0))

    assert response.status_code == 400
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['errors']) == 1
    assert result['errors'][0]['code'] == ErrorCode.REGISTRATION_INVALID_EMAIL.value['code']


def test_validate_registration_username_taken(test_client, setup_users):
    response = test_client.get('/users/validate_registration/' + create_token('A', 'a@bbb.cc', '0000', 0))

    assert response.status_code == 400
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['errors']) == 1
    assert result['errors'][0]['code'] == ErrorCode.REGISTRATION_USERNAME_TAKEN.value['code']


def test_validate_registration_email_taken(test_client, setup_users):
    response = test_client.get('/users/validate_registration/' + create_token('abc', 'a@AA.aa', '0000', 0))

    assert response.status_code == 400
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['errors']) == 1
    assert result['errors'][0]['code'] == ErrorCode.REGISTRATION_EMAIL_REGISTERED.value['code']


def test_validate_registration_email_blacklisted(test_client, setup_users):
    response = test_client.get('/users/validate_registration/' + create_token('alpha', 'a@ZZZ.com', '0000', 0))

    assert response.status_code == 400
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['errors']) == 1
    assert result['errors'][0]['code'] == ErrorCode.REGISTRATION_BLACKLISTED_EMAIL.value['code']


def test_validate_registration_success(test_client, setup_users):
    response = test_client.get(
        '/users/validate_registration/' + create_token('alpha', 'a@faforever.com', '0000', time.time() + 60))

    assert response.status_code == 200

    with db.connection:
        cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM login WHERE login = 'alpha'")

        result = cursor.fetchone()
        user_id = result['id']

        assert result['login'] == 'alpha'
        assert result['email'] == 'a@faforever.com'
        assert result['password'] == '0000'

        cursor.execute("SELECT * FROM global_rating WHERE id = %s" % user_id)
        assert cursor.fetchone() is not None

        cursor.execute("SELECT * FROM ladder1v1_rating WHERE id = %s" % user_id)
        assert cursor.fetchone() is not None


def test_validate_token_expired(test_client, setup_users):
    response = test_client.get(
        '/users/validate_registration/' + create_token('alpha', 'a@faforever.com', '0000', time.time() - 60))

    assert response.status_code == 400
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['errors']) == 1
    assert result['errors'][0]['code'] == ErrorCode.REGISTRATION_TOKEN_EXPIRED.value['code']
