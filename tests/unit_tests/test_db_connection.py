import json

import pytest
from faf import db


@pytest.fixture
def clans(request):
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("DELETE FROM clan_list")
        cursor.execute("""INSERT INTO clan_list VALUES
        (21,'2014-02-16 19:26:41',1,'FAF_Developer','DEV',447,447,'Developers, that try to improve FAF.')""")

    def finalizer():
        with db.connection:
            cursor = db.connection.cursor()
            cursor.execute("DELETE FROM clan_list")

    request.addfinalizer(finalizer)

def test_clan_list(test_client, clans):
    response = test_client.get('/clans')
    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 1

    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("DELETE FROM clan_list")
        cursor.execute("""INSERT INTO clan_list VALUES
         (25,'2014-02-16 21:05:46',1,'Obliterating Wave','O-W',450,450,NULL)""")

    response = test_client.get('/clans')
    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 2

def test_clan_list_sql(test_client, clans):
    response = test_client.get('/clans')
    result = json.loads(response.data.decode('utf-8'))
    assert 'data' in result
    assert len(result['data']) == 1

    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("DELETE FROM clan_list")
        cursor.execute("""INSERT INTO clan_list VALUES
         (25,'2014-02-16 21:05:46',1,'Obliterating Wave','O-W',450,450,NULL)""")

        cursor.execute('SELECT * FROM clans WHERE status = 1')
        result = cursor.fetchall()
        assert len(result) == 2
