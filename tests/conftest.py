import importlib

import pytest

import api


@pytest.fixture
def app():
    importlib.reload(api)
    importlib.reload(api.mods)
    importlib.reload(api.bugreports)
    importlib.reload(api.maps)
    importlib.reload(api.events)
    importlib.reload(api.achievements)
    importlib.reload(api.leaderboards)
    importlib.reload(api.clans)
    importlib.reload(api.coop)
    importlib.reload(api.players)
    importlib.reload(api.users_route)

    api.app.config.from_object('config')
    api.app.debug = True
    api.api_init()
    return api.app


@pytest.fixture
def test_client(app):
    return app.test_client()
