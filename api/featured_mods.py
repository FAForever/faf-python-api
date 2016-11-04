from faf.api.featured_mod_schema import FeaturedModSchema
from flask import request

from api import app
from api.query_commons import fetch_data

SELECT_EXPRESSIONS = {
    'id': 'id',
    'technical_name': 'gamemod',
    'display_name': 'name',
    'description': 'description',
    'visible': 'publish',
    'display_order': '`order`',
    'git_url': 'git_url',
    'git_branch': 'git_branch'
}

FEATURED_MODS_TABLE = 'game_featuredMods'
MAX_PAGE_SIZE = 1000


@app.route('/featured_mods')
def featured_mods():
    """
    Lists featured mods.

    **Example Request**:

    .. sourcecode:: http

       GET /featured_mods

    **Example Response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: text/javascript

        {
          "data": [
            {
              "attributes": {
                "id": "123",
                "technical_name": "faf",
                "display_name": "FA Forever",
                "description": "<html>HTML Description</html>",
                "visible": true,
                "display_order": 1,
                "git_url": "https://github.com/FAForever/fa.git",
                "git_branch": "master"
              },
              "id": "123",
              "type": "featured_mod"
            },
            ...
          ]
        }


    """
    result = fetch_data(FeaturedModSchema(), FEATURED_MODS_TABLE, SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request)

    return result
