import importlib
import pytest
import api


@pytest.fixture
def app():
    importlib.reload(api)
    importlib.reload(api.mods)
    importlib.reload(api.maps)
    importlib.reload(api.events)
    importlib.reload(api.achievements)
    importlib.reload(api.leaderboards)
    importlib.reload(api.replays)

    api.app.config.from_object('config')
    api.debug = True
    api.api_init()
    return api.app


@pytest.fixture
def test_client(app):
    return app.test_client()
