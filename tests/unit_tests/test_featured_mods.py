import json

import pytest

from faf import db


@pytest.fixture
def featured_mods():
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("DELETE FROM game_featuredMods")
        # TODO use common fixtures
        cursor.execute("""insert into game_featuredMods
(id, gamemod, description, name, publish, `order`, git_url, git_branch) values
(1, 'faf', '<html>Description</html>', 'FA Forever', 1, 1, 'https://github.com/FAForever/fa.git', 'master'),
(2, 'fafbeta', '<html>Description</html>', 'FA Forever Beta', 1, 2, 'https://github.com/FAForever/fa.git', 'fafbeta')
""")


def test_featured_mods(test_client, featured_mods):
    response = test_client.get('/featured_mods')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 2

    assert result['data'][0]['id'] == '1'
    assert result['data'][0]['attributes']['technical_name'] == 'faf'
    assert result['data'][0]['attributes']['display_name'] == 'FA Forever'
    assert result['data'][0]['attributes']['description'] == '<html>Description</html>'
    assert result['data'][0]['attributes']['visible']
    assert result['data'][0]['attributes']['display_order'] == 1
    assert result['data'][0]['attributes']['git_url'] == 'https://github.com/FAForever/fa.git'
    assert result['data'][0]['attributes']['git_branch'] == 'master'
