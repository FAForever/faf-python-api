import importlib
import json

import pytest

import api
from api.deploy import deploy_route
from api.error import ErrorCode


@pytest.fixture()
def setup_config():
    importlib.reload(api)
    importlib.reload(api.deploy)

    api.app.config.from_object('config')
    api.api_init()
    api.app.debug = True


def test_deploy_route(mocker, setup_config):
    mocker.patch("api.deploy.deploy_game")

    deploy_route("faf", "master", "faf", "12345")

    assert api.deploy.deploy_game.call_count == 1


def test_github_no_push(mocker, setup_config, test_client):
    mocker.patch("api.deploy.deploy_route")

    response = test_client.post('/github',
                                content_type='application/json',
                                headers={'X-Github-Event': 'branch',
                                         'X-GitHub-Delivery': 'f3853a00-c4b8-11e6-8fa5-b9f961ac9bc1'},
                                data=json.dumps({'content': 'empty'}))

    assert response.status_code == 200
    assert api.deploy.deploy_route.call_count == 0


def test_github_push_no_branch(mocker, setup_config, test_client):
    response = test_client.post('/github',
                                content_type='application/json',
                                headers={'X-Github-Event': 'push',
                                         'X-GitHub-Delivery': 'f3853a00-c4b8-11e6-8fa5-b9f961ac9bc1'},
                                data=json.dumps({'content': 'empty'}))

    assert response.status_code == 400
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['errors']) == 1
    assert result['errors'][0]['code'] == ErrorCode.INVALID_BRANCH.value['code']


def test_github_push_invalid_branch(mocker, setup_config, test_client):
    response = test_client.post('/github',
                                content_type='application/json',
                                headers={'X-Github-Event': 'push',
                                         'X-GitHub-Delivery': 'f3853a00-c4b8-11e6-8fa5-b9f961ac9bc1'},
                                data=json.dumps({'ref': 'refs/heads/invalid_branch'}))

    assert response.status_code == 400
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert len(result['errors']) == 1
    assert result['errors'][0]['code'] == ErrorCode.INVALID_BRANCH.value['code']
