import json

import pytest
from faf import db


@pytest.fixture
def clans(request):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("DELETE FROM clan_list")
        cursor.execute("""INSERT INTO clan_list VALUES
        (21,'2014-02-16 19:26:41',1,'FAF_Developer','DEV',447,447,'Developers, that try to improve FAF.'),
        (24,'2014-02-16 21:05:31',1,'Bad Company','BC',449,449,'This clan was founded by a player called Epic, who is sadly not active anymore. It is classified by its democratic system (new members need to pass a vote), and also a minimum rating of 1500 is required (exceptions under special circumstances are possible). Bad Company developed into a clan regularly hosting high class teamgames and consisting of high-level players. It won the clan tournament \"Intergalactic Colosseum 6\" ahead of any other participating clan. To join BC, you should pm any of our members.'),
        (25,'2014-02-16 21:05:46',1,'Obliterating Wave','O-W',450,450,NULL),
        (26,'2014-02-16 21:08:29',1,'Voice of Reason','VoR',457,457,'Aim; To be on the battlefield brave, without worry or fear - Stride for your target and know, your back is covered.\n~We are, \ncumulatively the Voice of Reason, together we banish nubism~\n'),
        (27,'2014-02-16 21:28:00',1,'Mockingjay Clan','MC',448,447,'A pack of friends addicted to Setons Clutch. Feel free to ask as about 4v4 on this amazing map.'),
        (30,'2014-02-16 22:11:44',1,'Special Forces','SFo',473,473,'The Special Forces are back in action and fighting harder than ever before.'),
        (31,'2014-02-16 22:12:39',1,'Totally English Annihilators','TEA',474,474,'www.TEA-Clan.co.uk\n\nA clan for the English who get along, we are not elitist, just nationalist.\n\nAny UK player with a good attitude is welcome.\n\nMessage me on the forum or on faf if you would like to apply to join.'),
        (32,'2014-02-16 22:39:03',1,'OverCharge','OC',453,453,NULL),
        (33,'2014-02-16 23:10:40',1,'New Roots','NR',447,479,'loading...')""")

    def finalizer():
        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute("DELETE FROM clan_list")

    request.addfinalizer(finalizer)

@pytest.fixture
def clan_members(request):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("DELETE FROM clan_members")
        cursor.execute("""INSERT INTO clan_members (`clan_id`, `player_id`) VALUES
        (21,447), (21, 449), (21, 474), (24, 447), (24, 449), (25, 447)""")

    def finalizer():
        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute("DELETE FROM clan_members")

    request.addfinalizer(finalizer)

@pytest.fixture
def clan_login(request):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("DELETE FROM login")
        cursor.execute("""INSERT INTO login (id, login, password, email) VALUES
        (447, 'Dragonfire', '', 'a'),
        (449, 'Blackheart', '', 'b'),
        (448, 'machina', '', 'c'),
        (453, 'Kammer', '', 'd'),
        (450, 'reddev32', '', 'e'),
        (457, 'VoR_Tex', '', 'f'),
        (473, 'Koecher', '', 'g'),
        (474, 'Pathogen', '', 'h'),
        (479, 'Stromfresser', '', 'i')""")

    def finalizer():
        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute("DELETE FROM login")

    request.addfinalizer(finalizer)

def test_clan_list(test_client, clans, clan_members, clan_login):
    response = test_client.get('/clans')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 9

    for item in result['data']:
        assert 'clan_id' in item['attributes']
        assert 'status' in item['attributes']
        assert 'clan_name' in item['attributes']
        assert 'clan_tag' in item['attributes']
        assert 'clan_leader_id' in item['attributes']
        assert 'clan_founder_id' in item['attributes']
        assert 'clan_desc' in item['attributes']
        assert 'create_date' in item['attributes']
        assert 'leader_name' in item['attributes']
        assert 'founder_name' in item['attributes']

    assert result['data'][0]['attributes']['clan_members'] == 3

def test_clan_founder_names(test_client, clans, clan_login):
    response = test_client.get('/clans')
    result = json.loads(response.data.decode('utf-8'))
    assert len(result['data']) == 9
    assert result['data'][0]['attributes']['founder_name'] == 'Dragonfire'
    assert result['data'][1]['attributes']['founder_name'] == 'Blackheart'
    assert result['data'][2]['attributes']['founder_name'] == 'reddev32'
    assert result['data'][3]['attributes']['founder_name'] == 'VoR_Tex'
    assert result['data'][4]['attributes']['founder_name'] == 'machina'
    assert result['data'][5]['attributes']['founder_name'] == 'Koecher'
    assert result['data'][6]['attributes']['founder_name'] == 'Pathogen'
    assert result['data'][7]['attributes']['founder_name'] == 'Kammer'
    assert result['data'][8]['attributes']['founder_name'] == 'Dragonfire'

def test_clan_leader_names(test_client, clans, clan_login):
    response = test_client.get('/clans')
    result = json.loads(response.data.decode('utf-8'))
    assert len(result['data']) == 9
    assert result['data'][0]['attributes']['leader_name'] == 'Dragonfire'
    assert result['data'][1]['attributes']['leader_name'] == 'Blackheart'
    assert result['data'][2]['attributes']['leader_name'] == 'reddev32'
    assert result['data'][3]['attributes']['leader_name'] == 'VoR_Tex'
    assert result['data'][4]['attributes']['leader_name'] == 'Dragonfire'
    assert result['data'][5]['attributes']['leader_name'] == 'Koecher'
    assert result['data'][6]['attributes']['leader_name'] == 'Pathogen'
    assert result['data'][7]['attributes']['leader_name'] == 'Kammer'
    assert result['data'][8]['attributes']['leader_name'] == 'Stromfresser'

def test_invalid_clan(test_client):
    response = test_client.get('/clan/42')

    # TODO: is this correct, or should we return 404?
    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert {} == result

def test_invalid_clan_with_data(test_client, clans, clan_members, clan_login):
    response = test_client.get('/clan/42')

    # TODO: is this correct, or should we return 404?
    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert {} == result

def test_clan_details(test_client, clans, clan_members, clan_login):
    response = test_client.get('/clan/21')

    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    result = json.loads(response.data.decode('utf-8'))
    assert 'clan_details' in result
    assert 'members' in result
    assert len(result['clan_details']) == 1
    assert len(result['members']) == 3

    for item in result['clan_details']:
        assert 'clan_id' in item
        assert 'status' in item
        assert 'clan_name' in item
        assert 'clan_tag' in item
        assert 'clan_leader_id' in item
        assert 'clan_founder_id' in item
        assert 'clan_desc' in item
        assert 'create_date' in item
        assert 'leader_name' in item
        assert 'founder_name' in item

    assert result['members'][0]['player_name'] == 'Dragonfire'    
    assert result['members'][1]['player_name'] == 'Blackheart'    
    assert result['members'][2]['player_name'] == 'Pathogen'    


