import urllib.parse
from functools import partial

from faf import db
from faf.api.featured_mod_file_schema import FeaturedModFileSchema
from faf.api.featured_mod_schema import FeaturedModSchema
from flask import request
from pymysql.cursors import DictCursor

from api import app, cache, default_cache_key
from api.error import Error, ErrorCode, ApiException
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

FILES_SELECT_EXPRESSIONS = {
    'id': 'u.id',
    'version': 'u.version',
    'group': 'b.path',
    'name': 'b.filename',
    'md5': 'u.md5',
    # url will be URL encoded and made absolute in enricher
    'url': "u.name"
}

FILES_TABLE_FORMAT = """updates_{0}_files u
    LEFT JOIN updates_{0}_files u2
        ON u.fileid = u2.fileid
            AND u.version < u2.version
    LEFT JOIN updates_{0} b
        ON b.id = u.fileId
    WHERE u2.version IS NULL """

FEATURED_MODS_TABLE = 'game_featuredMods'

MAX_PAGE_SIZE = 1000


@app.route('/featured_mods')
@cache.cached(timeout=300, key_prefix=default_cache_key)
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


@app.route('/featured_mods/<int:mod_id>')
@cache.cached(timeout=300, key_prefix=default_cache_key)
def get_featured_mod(mod_id):
    """
    Gets a  featured mod.

    **Example Request**:

    .. sourcecode:: http

       GET /featured_mods

    **Example Response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: text/javascript

        {
          "data": {
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
          }
        }


    """
    return fetch_data(FeaturedModSchema(), FEATURED_MODS_TABLE, SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request,
                      many=False, where='id = %s', args=mod_id)


@app.route('/featured_mods/<string:id>/files')
@cache.cached(timeout=300, key_prefix=default_cache_key)
def featured_mod_files_latest(id):
    """
    Lists the latest files of the specified mod.

    **Example Request**:

    .. sourcecode:: http

       GET /featured_mods/123/files

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
                "md5": "1bdb6505a6af741509c9d3ed99670b79",
                "version": "ee2df6c3cb80dc8258428e8fa092bce1",
                "name": "ForgedAlliance.exe",
                "group": "bin",
                "url": "http://content.faforever.com/faf/updaterNew/updates_faf_files/ForgedAlliance.3659.exe"
              },
              "id": "123",
              "type": "featured_mod_file"
            },
            ...
          ]
        }
    """
    return featured_mod_files(id, 'latest')


@app.route('/featured_mods/<string:id>/files/<string:version>')
@cache.cached(timeout=300, key_prefix=default_cache_key)
def featured_mod_files(id, version):
    """
    Lists the files of a specific version of the specified mod. If the version is "latest", the latest version is
    returned.

    **Example Request**:

    .. sourcecode:: http

       GET /featured_mods/123/files/3663

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
                "md5": "1bdb6505a6af741509c9d3ed99670b79",
                "version": "ee2df6c3cb80dc8258428e8fa092bce1",
                "name": "ForgedAlliance.exe",
                "group": "bin",
                "url": "http://content.faforever.com/faf/updaterNew/updates_faf_files/ForgedAlliance.3659.exe"
              },
              "id": "123",
              "type": "featured_mod_file"
            },
            ...
          ]
        }
    """

    mods = get_featured_mods()
    if id not in mods:
        raise ApiException([Error(ErrorCode.UNKNOWN_FEATURED_MOD, id)])

    featured_mod_name = 'faf' if mods.get(id) == 'ladder1v1' else mods.get(id)
    files_table = FILES_TABLE_FORMAT.format(featured_mod_name)

    where = ''
    args = None
    if version and version != 'latest':
        where += ' AND u.version <= %s'
        args = (version,)

    return fetch_data(FeaturedModFileSchema(), files_table, FILES_SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request,
                      enricher=partial(file_enricher, 'updates_{}_files'.format(featured_mod_name)),
                      where_extension=where,
                      args=args)


def file_enricher(files_folder, featured_mod_file):
    if 'url' not in featured_mod_file:
        return

    featured_mod_file['url'] = '{}/faf/updaterNew/{}/{}'.format(
        app.config['CONTENT_URL'], files_folder, urllib.parse.quote(featured_mod_file['url']))


@cache.cached(timeout=300, key_prefix='featured_mods')
def get_featured_mods():
    with db.connection:
        cursor = db.connection.cursor(DictCursor)
        cursor.execute("SELECT id, gamemod FROM game_featuredMods")
        result = cursor.fetchall()

    return {str(row['id']): row['gamemod'] for row in result}
