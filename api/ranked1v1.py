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
    'is_active': 'r.is_active',
    'rating': 'ROUND(r.mean - 3 * r.deviation)',
    'ranking': '@rownum:=@rownum+1'
}

TABLE1V1 = 'ladder1v1_rating r JOIN login l on r.id = l.id, (SELECT @rownum:=%(row_num)s) n'
TABLEGLOBAL = 'global_rating r JOIN login l on r.id = l.id, (SELECT @rownum:=%(row_num)s) n'


@app.route('/ranked1v1')
def ranked1v1():
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

    return fetch_data(Ranked1v1Schema(), TABLE1V1, SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request, sort='-rating',
                      args=args, where=where)


@app.route('/ranked1v1/<int:player_id>')
def ranked1v1_get(player_id):
    select_expressions = SELECT_EXPRESSIONS.copy()
    select_expressions['ranking'] = """(SELECT count(*) FROM ladder1v1_rating
                                        WHERE ROUND(mean - 3 * deviation) >= ROUND(r.mean - 3 * r.deviation)
                                        AND is_active = 1
                                        AND numGames > 0)
                                        """

    result = fetch_data(Ranked1v1Schema(), TABLE1V1, select_expressions, MAX_PAGE_SIZE, request,
                        many=False, where='r.id=%(id)s', args=dict(id=player_id, row_num=0))

    if 'id' not in result['data']:
        return {'errors': [{'title': 'No entry with this id was found'}]}, 404

    return result


@app.route("/ranked1v1/stats")
def ranked1v1_stats():
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


def append_select_expression():
    select = SELECT_EXPRESSIONS.copy()
    select['won_games'] = 'r.winGames'
    select['lost_games'] = 'r.numGames - r.winGames'
    select['winning_percentage'] = 'ROUND((r.winGames/r.numGames) * 100)'
    return select
