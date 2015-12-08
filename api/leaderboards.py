from faf.api.leaderboard_schema import LeaderboardSchema
from flask import request

from api import app
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

TABLE = 'ladder1v1_rating r JOIN login l on r.id = l.id, (SELECT @rownum:=0) n'


@app.route('/leaderboards')
def leaderboards():
    return fetch_data(LeaderboardSchema(), TABLE, SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request, sort='ranking')


@app.route('/leaderboards/<int:id>')
def leaderboard(id):
    result = fetch_data(LeaderboardSchema(), TABLE, SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request,
                        many=False, where='r.id=%s', args=id)

    if 'id' not in result['data']:
        return {'errors': [{'title': 'No entry with this id was found'}]}, 404

    return result
