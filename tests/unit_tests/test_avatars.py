import importlib
import json
import re
from unittest.mock import Mock
import pytest
import datetime
import os
import tempfile, shutil

import faf.db as db
import api
from api.user import User, UserGroup
from api.error import ErrorCode
from api.avatars import Avatar

@pytest.fixture
def avatar_setup(request):
    importlib.reload(api)
    importlib.reload(api.oauth_handlers)
    importlib.reload(api.avatars)
    importlib.reload(api.user)

    api.app.config.from_object('config')
    avatar_dir = tempfile.mkdtemp()
    api.app.config['AVATAR_FOLDER'] = avatar_dir
    api.api_init()
    api.app.debug = True


    app = api.app.test_client()

    def finalizer():
        shutil.rmtree(avatar_dir)
        db.connection.close()

    request.addfinalizer(finalizer)

@pytest.fixture
def oauth(request):
    # we need to create a user that has a group so the api can check for it
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("""insert into login
        (login, password, email)
        values
        ('Test Admin', '', 'admin@example.com')""")
        user_id = cursor.lastrowid
        cursor.execute("""insert into lobby_admin
        (`user_id`, `group`)
        values
        (%s, 2)""", user_id)

    def get_token(access_token=None, refresh_token=None):
        user = User(id=user_id)
        return Mock(
            user=user,
            expires=datetime.datetime.now() + datetime.timedelta(hours=1),
            scopes=['public_profile']
        )

    importlib.reload(api)
    importlib.reload(api.oauth_handlers)
    importlib.reload(api.avatars)

    api.app.config.from_object('config')
    avatar_dir = tempfile.mkdtemp()
    api.app.config['AVATAR_FOLDER'] = avatar_dir
    api.api_init()
    api.app.debug = True

    def finalizer():
        shutil.rmtree(avatar_dir)
        with db.connection:
            db.connection.cursor().execute('DELETE FROM login WHERE id=%s', user_id)
        db.connection.close()
    request.addfinalizer(finalizer)

    api.oauth.tokengetter(get_token)

    return api.app.test_client()

def test_avatar_put(oauth):
    # PUT avatar
    avatar_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../data/faf_32x32.png')
    with open(avatar_file, 'rb') as af:
        response = oauth.put('/avatar',
                data=dict(
                    file=(af, os.path.basename(avatar_file)),
                    tooltip='avatar test'
                    ))
    # check PUT return
    response_data = json.loads(response.data.decode("utf-8"))
    print(response_data)
    assert 200 == response.status_code
    new_avatar = Avatar.get_by_id(response_data['id'])
    assert new_avatar is not None
    assert new_avatar.dict() == response_data

def test_avatar_post(oauth):
    avatar = Avatar(filename='notreal.png', tooltip='test tooltip')
    avatar.insert()

    # POST avatar
    response = oauth.post('/avatar',
            data=dict(
                id=avatar.id,
                tooltip='avatar test edited'
                ))
    assert 200 == response.status_code
    response_data = json.loads(response.data.decode("utf-8"))
    new_avatar = Avatar.get_by_id(response_data['id'])
    assert new_avatar is not None
    assert 'avatar test edited' == response_data['tooltip']
    assert new_avatar.dict() == response_data

def test_avatar_get(test_client):
    avatar = Avatar(filename='notreal_test_get.png', tooltip='test tooltip')
    avatar.insert()

    # GET avatar
    response = test_client.get('/avatar?id={}'.format(avatar.id))
    assert 200 == response.status_code
    assert avatar.dict() == json.loads(response.data.decode("utf-8"))

def test_avatar_get_all(test_client, avatar_setup):
    # GET avatar list
    response = test_client.get('/avatar')
    response_data = json.loads(response.data.decode("utf-8"))
    assert 200 == response.status_code
    assert len(response_data) >= 0

def test_avatar_delete(oauth):
    avatar = Avatar(filename='notreal_test_delete.png', tooltip='test tooltip')
    avatar.insert()

    # DELETE avatar
    response = oauth.delete('/avatar', data=dict(id=avatar.id))
    assert 204 == response.status_code
    assert Avatar.get_by_id(avatar.id) is None

@pytest.fixture
def avatar_user(request):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("""insert into login
        (login, password, email)
        values
        ('Test User', '', 'user@example.com')""")
        user_id = cursor.lastrowid

    user = User.get_by_id(user_id)
    print(user.usergroup())

    avatar = Avatar(filename='notreal_test_userava.png', tooltip='test tooltip')
    avatar.insert()
    Avatar.add_user_avatars(user_id, [avatar])

    def finalizer():
        Avatar.remove_user_avatars(user, [Avatar(**a) for a in Avatar.get_user_avatars(user)])
        avatar.delete()

        with db.connection:
            db.connection.cursor().execute('DELETE FROM login WHERE id=%s', user_id)
        db.connection.close()
    request.addfinalizer(finalizer)

    return user, avatar

def test_user_avatar_get(test_client, avatar_user):
    user, avatar = avatar_user

    response = test_client.get('/user_avatars?id={}'.format(user.id))
    response_data = json.loads(response.data.decode("utf-8"))
    assert 200 == response.status_code
    assert len(response_data) >= 0
    assert avatar.id in [a['id'] for a in response_data]

@pytest.mark.skip
def test_user_avatar_cannot_be_added_by_unauthed_user(test_client, avatar_user):
    user, old_avatar = avatar_user

    new_avatar = Avatar(filename='notreal_test_userava_add_unauth.png', tooltip='test tooltip')
    new_avatar.insert()

    user_id=user.id
    avatar_id=new_avatar.id

    response = test_client.post('/user_avatars', data=dict(user_id=user_id, avatar_id=avatar_id))
    assert 401 == response.status_code

def test_user_avatar_can_be_added_by_authed_user(oauth, avatar_user):
    user, old_avatar = avatar_user

    new_avatar = Avatar(filename='notreal_test_userava_add_auth.png', tooltip='test tooltip')
    new_avatar.insert()

    response = oauth.post('/user_avatars', data=dict(user_id=user.id, avatar_id=new_avatar.id))
    assert 200 == response.status_code
    assert new_avatar.id in [a['id'] for a in Avatar.get_user_avatars(user)]

def test_user_avatar_delete(oauth, avatar_user):
    user, old_avatar = avatar_user

    response = oauth.delete('/user_avatars', data=dict(user_id=user.id, avatar_id=old_avatar.id))
    assert 204 == response.status_code
    assert old_avatar.id not in [a['id'] for a in Avatar.get_user_avatars(user)]
