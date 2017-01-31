import json

import pytest
from faf import db


@pytest.fixture
def featured_mods():
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("DELETE FROM game_featuredMods")
        # TODO use common fixtures
        cursor.execute("""
insert into game_featuredMods
    (id, gamemod, description, name, publish, `order`, git_url, git_branch) values
    (1, 'faf', '<html>Description</html>', 'FA Forever', 1, 1, 'https://github.com/FAForever/fa.git', 'master'),
    (2, 'fafbeta', '<html>Description</html>', 'FA Forever Beta', 1, 2, 'https://github.com/FAForever/fa.git', 'fafbeta');

delete from updates_faf;
insert into updates_faf (id, filename, path) values
    (1, 'ForgedAlliance.exe', 'bin'),
    (11, 'effects.nx2', 'gamedata'),
    (12, 'env.nx2', 'gamedata');

delete from updates_faf_files;
insert into updates_faf_files (id, fileId, version, name, md5, obselete) values
    (711, 1, 3658, 'ForgedAlliance.3658.exe', '2cd7784fb131ea4955e992cfee8ca9b8', 0),
    (745, 1, 3659, 'ForgedAlliance.3659.exe', 'ee2df6c3cb80dc8258428e8fa092bce1', 0),
    (710, 11, 3657, 'effects_0.3657.nxt', 'edd083b3dc54ec79c354be2b845f25ee', 0),
    (723, 11, 3658, 'effects_0.3658.nxt', '3758baad77531dd5323c766433412e91', 0),
    (734, 11, 3659, 'effects_0.3659.nxt', '3758baad77531dd5323c766433412e91', 0),
    (680, 12, 3656, 'env_0.3656.nxt', '32a50729cb5155ec679771f38a151d29', 0);
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


def test_featured_mod_files_latest(test_client, featured_mods):
    response = test_client.get('/featured_mods/1/files')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    assert result == {'data': [
        {
            'id': '745',
            'attributes': {
                'id': '745',
                'md5': 'ee2df6c3cb80dc8258428e8fa092bce1',
                'url': 'http://content.faforever.com/faf/updaterNew/updates_faf_files/ForgedAlliance.3659.exe',
                'group': 'bin',
                'name': 'ForgedAlliance.exe',
                'version': '3659'
            },
            'type': 'featured_mod_file'
        },
        {
            'id': '734',
            'attributes': {
                'id': '734',
                'md5': '3758baad77531dd5323c766433412e91',
                'url': 'http://content.faforever.com/faf/updaterNew/updates_faf_files/effects_0.3659.nxt',
                'group': 'gamedata',
                'name': 'effects.nx2',
                'version': '3659'
            },
            'type': 'featured_mod_file'
        },
        {
            'id': '680',
            'attributes': {
                'id': '680',
                'md5': '32a50729cb5155ec679771f38a151d29',
                'url': 'http://content.faforever.com/faf/updaterNew/updates_faf_files/env_0.3656.nxt',
                'group': 'gamedata',
                'name': 'env.nx2',
                'version': '3656'
            },
            'type': 'featured_mod_file'
        }
    ]}


def test_featured_mod_files_3656(test_client, featured_mods):
    response = test_client.get('/featured_mods/1/files/3656')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    assert result == {'data': [
        {
            'id': '680',
            'attributes': {
                'id': '680',
                'md5': '32a50729cb5155ec679771f38a151d29',
                'url': 'http://content.faforever.com/faf/updaterNew/updates_faf_files/env_0.3656.nxt',
                'group': 'gamedata',
                'name': 'env.nx2',
                'version': '3656'
            },
            'type': 'featured_mod_file'
        }
    ]}


def test_featured_mod_files_unknown_mod(test_client, featured_mods):
    response = test_client.get('/featured_mods/1111/files')

    assert response.status_code == 400
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    assert result == {
        'errors': [{
            'meta': {'args': ['1111']},
            'detail': 'There is no featured mod with ID "1111".',
            'code': 142,
            'title': 'Unknown featured mod'
        }]
    }


def test_get_featured_mod(test_client, featured_mods):
    response = test_client.get('/featured_mods/1')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))

    assert result == {
        'data': {
            'id': '1',
            'type': 'featured_mod',
            'attributes': {
                'id': '1',
                'display_order': 1,
                'display_name': 'FA Forever',
                'git_branch': 'master',
                'technical_name': 'faf',
                'description': '<html>Description</html>',
                'git_url': 'https://github.com/FAForever/fa.git',
                'visible': True
            }
        }
    }
