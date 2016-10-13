import json

import pytest
from faf import db

from api.error import ErrorCode


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


def test_create_account_invalid_email(test_client, setup_users):
    response = test_client.post('/users/create_account',
                                data={'name': 'a', 'email': 'abbb.cc', 'pw_hash': '0000'})

    assert response.status_code == 400
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['errors']) == 1
    assert result['errors'][0]['code'] == ErrorCode.REGISTRATION_INVALID_EMAIL.value['code']


def test_create_account_invalid_username(test_client, setup_users):
    response = test_client.post('/users/create_account',
                                data={'name': 'a,b', 'email': 'a@bbb.cc', 'pw_hash': '0000'})

    assert response.status_code == 400
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['errors']) == 1
    assert result['errors'][0]['code'] == ErrorCode.REGISTRATION_INVALID_USERNAME.value['code']


def test_create_account_username_taken(test_client, setup_users):
    response = test_client.post('/users/create_account',
                                data={'name': 'A', 'email': 'a@bbb.cc', 'pw_hash': '0000'})

    assert response.status_code == 400
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['errors']) == 1
    assert result['errors'][0]['code'] == ErrorCode.REGISTRATION_USERNAME_TAKEN.value['code']


def test_create_account_email_taken(test_client, setup_users):
    response = test_client.post('/users/create_account',
                                data={'name': 'abc', 'email': 'a@AA.aa', 'pw_hash': '0000'})

    assert response.status_code == 400
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['errors']) == 1
    assert result['errors'][0]['code'] == ErrorCode.REGISTRATION_EMAIL_REGISTERED.value['code']


def test_create_account_email_blacklisted(test_client, setup_users):
    response = test_client.post('/users/create_account',
                                data={'name': 'alpha', 'email': 'a@ZZZ.com', 'pw_hash': '0000'})

    assert response.status_code == 400
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['errors']) == 1
    assert result['errors'][0]['code'] == ErrorCode.REGISTRATION_BLACKLISTED_EMAIL.value['code']
