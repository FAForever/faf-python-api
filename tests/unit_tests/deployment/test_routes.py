import json
from unittest.mock import MagicMock

import pytest

from api.deployment.deployment_manager import DeploymentManager


@pytest.fixture
def setup_manager(app):
    github = MagicMock()
    response = MagicMock()
    response.status_code = 201
    github.create_deployment = MagicMock(return_value=response)
    slack = MagicMock()

    manager = DeploymentManager("testing", b"", "FAForever", github, slack)
    test_game_config = MagicMock()
    test_game_config.matches = MagicMock(return_value=True)

    manager.add(test_game_config)

    app.deployment_manager = manager

    return manager


def test_github_irrelevant_request(test_client, setup_manager):
    request_data = dict(
        repository=dict(
            name="fa",
            clone_url="https://github.com/FAForever/fa.git"
        )
    )

    response = test_client.post('/deployment/github',
                                headers=[('Content-Type', 'application/json'),
                                         ('X-GitHub-Delivery', 'test'),
                                         ('X-GitHub-Event', 'ping')],
                                data=json.dumps(request_data))

    assert response.status_code == 200
    assert "irrelevant" in response.data.decode("utf8")


def test_github_push_not_distinct(test_client, setup_manager):
    request_data = dict(
        repository=dict(
            name="fa",
            clone_url="https://github.com/FAForever/fa.git"
        ),
        ref='refs/heads/master',
        head_commit=dict(
            distinct=False
        )
    )

    response = test_client.post('/deployment/github',
                                headers=[('Content-Type', 'application/json'),
                                         ('X-GitHub-Delivery', 'test'),
                                         ('X-GitHub-Event', 'push')],
                                data=json.dumps(request_data))

    assert response.status_code == 200
    assert "commit already known" in response.data.decode("utf8")


def test_github_push_no_conf(test_client):
    github = MagicMock()
    slack = MagicMock()

    manager = DeploymentManager("testing", b"", "FAForever", github, slack)
    test_game_config = MagicMock()
    test_game_config.matches(MagicMock(return_value=False))

    manager.add(test_game_config)

    request_data = dict(
        repository=dict(
            name="fa",
            clone_url="https://github.com/FAForever/fa.git"
        ),
        ref='refs/heads/master',
        head_commit=dict(
            distinct=True,
            message="bugfix"
        )
    )

    response = test_client.post('/deployment/github',
                                headers=[('Content-Type', 'application/json'),
                                         ('X-GitHub-Delivery', 'test'),
                                         ('X-GitHub-Event', 'push')],
                                data=json.dumps(request_data))

    assert response.status_code == 200
    assert "no matching configuration" in response.data.decode("utf8")


def test_github_push_success(test_client, setup_manager):
    request_data = dict(
        repository=dict(
            name="fa",
            clone_url="https://github.com/FAForever/fa.git"
        ),
        ref='refs/heads/deploy/fafbeta',
        head_commit=dict(
            distinct=True,
            message="bugfix"
        )
    )

    response = test_client.post('/deployment/github',
                                headers=[('Content-Type', 'application/json'),
                                         ('X-GitHub-Delivery', 'test'),
                                         ('X-GitHub-Event', 'push')],
                                data=json.dumps(request_data))

    assert response.status_code == 201
    assert "deployment invoked" in response.data.decode("utf8")


def test_github_deploy_no_conf(test_client, app):
    github = MagicMock()
    response = MagicMock()
    response.status_code = 201
    github.create_deployment = MagicMock(return_value=response)
    slack = MagicMock()

    manager = DeploymentManager("testing", b"", "FAForever", github, slack)
    test_game_config = MagicMock()
    test_game_config.matches = MagicMock(return_value=False)

    manager.add(test_game_config)

    app.deployment_manager = manager

    request_data = dict(
        repository=dict(
            name="fa",
            clone_url="https://github.com/FAForever/fa.git"
        ),
        deployment=dict(
            id=1234,
            ref='refs/heads/nonexistingrepo',
            sha='commit_sha',
            environment='testing'
        ),
        head_commit=dict(
            distinct=True,
            message="bugfix"
        )
    )

    response = test_client.post('/deployment/github',
                                headers=[('Content-Type', 'application/json'),
                                         ('X-GitHub-Delivery', 'test'),
                                         ('X-GitHub-Event', 'deployment')],
                                data=json.dumps(request_data))

    assert response.status_code == 200
    assert "no matching configuration" in response.data.decode("utf8")


def test_github_deploy_success(test_client, setup_manager):
    request_data = dict(
        repository=dict(
            name="fa",
            clone_url="https://github.com/FAForever/fa.git"
        ),
        deployment=dict(
            id=1234,
            ref='refs/heads/deploy/fafbeta',
            sha='commit_sha',
            environment='testing'
        ),
        head_commit=dict(
            distinct=True,
            message="bugfix"
        )
    )

    response = test_client.post('/deployment/github',
                                headers=[('Content-Type', 'application/json'),
                                         ('X-GitHub-Delivery', 'test'),
                                         ('X-GitHub-Event', 'deployment')],
                                data=json.dumps(request_data))

    assert response.status_code == 201
    assert "deployment started" in response.data.decode("utf8")
