import pytest
import api

@pytest.fixture
def app():
    api.app.config.from_object('config')
    api.debug = True
    api.api_init()
    return api.app

@pytest.fixture
def test_client(app):
    return app.test_client()
