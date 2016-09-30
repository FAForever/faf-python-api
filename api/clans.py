import faf.db as db
from faf.api import ClanSchema
from flask import request

from api import app
from api.query_commons import fetch_data

MAX_PAGE_SIZE = 10000
CLAN_LIST = 'clan_list LEFT JOIN login AS leader ON clan_list.clan_leader_id = leader.id ' \
            + 'LEFT JOIN login AS founder ON clan_list.clan_founder_id = founder.id '

COUNT_MEMBERS = '(SELECT COUNT(0) FROM clan_members WHERE (clan_list.clan_id = clan_members.clan_id))'
SELECT_EXPRESSIONS = {
    'clan_id': 'clan_id',
    'status': 'status',
    'clan_name': 'clan_name',
    'clan_tag': 'clan_tag',
    'clan_leader_id': 'clan_leader_id',
    'clan_founder_id': 'clan_founder_id',
    'clan_tag_color': 'clan_tag_color',
    'clan_desc': 'clan_desc',
    'create_date': 'create_date',
    'leader_name': 'leader.login',
    'founder_name': 'founder.login',
    'clan_members': COUNT_MEMBERS
}


@app.route('/clans')
def clans():
    return fetch_data(ClanSchema(), CLAN_LIST, SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request)


@app.route('/clan/<int:id>')
def clan_get(id):
    with db.connection.cursor(db.pymysql.cursors.DictCursor) as cursor:
        cursor.execute(
            'SELECT clan_id, status, clan_name, clan_tag, clan_leader_id, clan_founder_id, clan_tag_color, clan_desc, '
            + 'create_date, leader.login leader_name, founder.login founder_name, ' + COUNT_MEMBERS + ' clan_members '
            + 'FROM ' + CLAN_LIST + 'WHERE clan_id = %s LIMIT 1', id)
        if cursor.rowcount == 1:
            clan_details = cursor.fetchall()
            cursor.execute('SELECT `player_id`, `login`.`login` `player_name`, `join_clan_date` '
                           + 'FROM `clan_members` LEFT JOIN `login` ON `clan_members`.`player_id` = `login`.`id` '
                           + 'WHERE `clan_id` = %s ', id)
            return {'clan_details': clan_details,
                    'members': cursor.fetchall()}
    return {}
