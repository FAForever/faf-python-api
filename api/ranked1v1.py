from faf.api.ranked1v1_schema import Ranked1v1Schema
from faf.api.ranked1v1_stats_schema import Ranked1v1StatsSchema
from flask import request
from pymysql.cursors import DictCursor

from api import app, InvalidUsage
from api.query_commons import fetch_data
from faf import db

ALLOWED_EXTENSIONS = {'zip'}
MAX_PAGE_SIZE = 5000

SELECT_EXPRESSIONS = {
    'id': 'r.id',
    'login': 'l.login',
    'mean': 'r.mean',
    'deviation': 'r.deviation',
    'num_games': 'r.numGames',
    'won_games': 'r.winGames',
    'is_active': 'r.is_active',
    'rating': 'ROUND(r.mean - 3 * r.deviation)',
    'ranking': '@rownum:=@rownum+1'
}

TABLE = 'ladder1v1_rating r JOIN login l on r.id = l.id, (SELECT @rownum:=%(row_num)s) n'


@app.route('/ranked1v1')
def ranked1v1():
    """
    Lists all ranked 1v1 players.

    **Example Request**:

    **Default Values**:
        page[number]=1

        page[size]=5000

    .. sourcecode:: http

       GET /ranked1v1
       Accept: application/vnd.api+json

    **Example Response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: text/javascript

        {
          "data": [
            {
              "attributes": {
                "deviation": 48.4808,
                "id": "781",
                "is_active": true,
                "login": "Zock",
                "mean": 2475.69,
                "num_games": 1285,
                "ranking": 1,
                "rating": 2330,
                "won_games": 946
              },
              "id": "781",
              "type": "ranked1v1"
            },
            ...
          ]
        }

    :param page[number]: The page number being requested (EX.: /ranked1v1?page[number]=2)
    :type page[number]: int
    :param page[size]: The total amount of players to grab by default (EX.: /ranked1v1?page[size]=10)
    :type page[size]: int
    :param filter[isActive]: Whether or not to filter active players or not (true or false) (EX.: /ranked1v1?filter[is_active]=true)
    :type filter[isActive]: boolean
    :param filter[player]: Allows search functionality in the ranked1v1 endpoint based upon the players login name (EX.: /ranked1v1?filter[player]=Zock)
    :type filter[player]: name
    :status 200: No error

    """
    if request.values.get('sort'):
        raise InvalidUsage('Sorting is not supported for ranked1v1')

    page = int(request.values.get('page[number]', 1))
    page_size = int(request.values.get('page[size]', MAX_PAGE_SIZE))
    player = request.args.get('filter[player]')
    row_num = (page - 1) * page_size

    args = {'row_num': row_num}

    where = ''
    active_filter = request.values.get('filter[is_active]')
    if active_filter:
        where += 'is_active = ' + ('1' if active_filter.lower() == 'true' else '0') + ' AND r.numGames > 0'

    if player:
        where += " l.login LIKE %(player)s"
        args['player'] = '%' + player + '%'

    return fetch_data(Ranked1v1Schema(), TABLE, SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request, sort='-rating',
                      args=args, where=where)


@app.route('/ranked1v1/<int:player_id>')
def ranked1v1_get(player_id):
    """
    Gets a ranked player. Player must be active, played more than one ranked game, and must have statistics associated
    with he/she.

    **Example Request**:

    .. sourcecode:: http

       GET /ranked1v1/781

    **Example Response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: text/javascript

        {
          "data": {
            "attributes": {
              "deviation": 48.4808,
              "id": "781",
              "is_active": true,
              "login": "Zock",
              "mean": 2475.69,
              "num_games": 1285,
              "ranking": 1,
              "rating": 2330,
              "won_games": 946
            },
            "id": "781",
            "type": "ranked1v1"
          }
        }

    :status 200: No error
    :status 404: No entry with this id was found

    """
    select_expressions = SELECT_EXPRESSIONS.copy()
    select_expressions['ranking'] = """(SELECT count(*) FROM ladder1v1_rating
                                        WHERE ROUND(mean - 3 * deviation) >= ROUND(r.mean - 3 * r.deviation)
                                        AND is_active = 1
                                        AND numGames > 0)
                                        """

    result = fetch_data(Ranked1v1Schema(), TABLE, select_expressions, MAX_PAGE_SIZE, request,
                        many=False, where='r.id=%(id)s', args=dict(id=player_id, row_num=0))

    if 'id' not in result['data']:
        return {'errors': [{'title': 'No entry with this id was found'}]}, 404

    return result


@app.route("/ranked1v1/stats")
def ranked1v1_stats():
    """
    Gets all player stats sorted by rankings.

    **Example Request**:

    .. sourcecode:: http

       GET /ranked1v1/stats

    **Example Response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: text/javascript

        {
          "data": {
            "attributes": {
              "rating_distribution": {
                "-100": 206,
                "-200": 192,
                "-300": 137,
                "-400": 77,
                "-500": 15,
                "-600": 10,
                "-700": 1,
                "0": 268,
                "100": 282,
                "1000": 122,
                "1100": 86,
                "1200": 72,
                "1300": 55,
                "1400": 42,
                "1500": 35,
                "1600": 25,
                "1700": 15,
                "1800": 14,
                "1900": 7,
                "200": 284,
                "2000": 5,
                "2100": 2,
                "2200": 1,
                "2300": 2,
                "300": 316,
                "400": 296,
                "500": 239,
                "600": 238,
                "700": 208,
                "800": 177,
                "900": 140
              }
            },
            "id": "/ranked1v1/stats",
            "type": "ranked1v1_stats"
          }
        }

    :status 200: No error

    """
    with db.connection:
        cursor = db.connection.cursor(DictCursor)
        cursor.execute("""
        SELECT
            FLOOR((mean - 3 * deviation)/100) * 100 AS `rating`,
            count(*) as count
        FROM ladder1v1_rating
        WHERE `is_active` = 1
            AND mean BETWEEN 0 AND 3000
            AND deviation <= 250
            AND numGames > 0
        GROUP BY `rating`
        ORDER BY CAST(`rating` as SIGNED) ASC;
        """)

        result = cursor.fetchall()

    data = dict(id='/ranked1v1/stats', rating_distribution={})

    for item in result:
        data['rating_distribution'][str(int(item['rating']))] = item['count']

    return Ranked1v1StatsSchema().dump(data, many=False).data
