import json
from flask import Response


def test_get_mods(test_client):
    response = test_client.get('/mods')

    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.content_type == 'application/vnd.api+json'

    response = json.loads(response.data.decode())
    assert 'data' in response

    data = response['data']

    for item in data:
        assert 'type' in item

