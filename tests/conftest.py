import importlib

import pytest
import api
import faf.db

@pytest.fixture
def app():
    importlib.reload(api)
    importlib.reload(api.mods)
    importlib.reload(api.bugreports)
    importlib.reload(api.maps)
    importlib.reload(api.events)
    importlib.reload(api.achievements)
    importlib.reload(api.games)
    importlib.reload(api.ranked1v1)
    importlib.reload(api.clans)

    api.app.config.from_object('config')
    api.app.debug = True
    api.api_init()
    # TODO: use a custom test db instead of the real instance
    # The real database is connected before each request, so we fake it
    # https://github.com/FAForever/api/issues/40
    faf.db.init_db(api.app.config)
    return api.app


@pytest.fixture
def test_client(app):
    return app.test_client()
