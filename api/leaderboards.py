from faf.api.leaderboard_schema import LeaderboardSchema
from flask import request

from api import app, InvalidUsage
from api.query_commons import fetch_data

ALLOWED_EXTENSIONS = {'zip'}
MAX_PAGE_SIZE = 1000

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


@app.route('/leaderboards')
def leaderboards():
    if request.values.get('sort'):
        raise InvalidUsage('Sorting is not supported for leaderboards')

    page = int(request.values.get('page[number]', 1))
    page_size = int(request.values.get('page[size]', MAX_PAGE_SIZE))
    row_num = (page - 1) * page_size

    where = ''
    active_filter = request.values.get('filter[is_active]')
    if active_filter:
        where += 'is_active = ' + ('1' if active_filter.lower() == 'true' else '0')

    return fetch_data(LeaderboardSchema(), TABLE, SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request, sort='-rating',
                      args=dict(row_num=row_num), where=where)


@app.route('/leaderboards/<int:player_id>')
def leaderboard(player_id):
    SELECT_EXPRESSIONS['ranking'] = """(SELECT count(*) FROM ladder1v1_rating
                                        WHERE ROUND(mean - 3 * deviation) >= ROUND(r.mean - 3 * r.deviation))"""

    result = fetch_data(LeaderboardSchema(), TABLE, SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request,
                        many=False, where='r.id=%(id)s', args=dict(id=player_id, row_num=0))

    if 'id' not in result['data']:
        return {'errors': [{'title': 'No entry with this id was found'}]}, 404

    return result
