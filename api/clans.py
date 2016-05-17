import faf.db as db

from faf.api import ClanSchema
from flask import request
from api.query_commons import fetch_data
from api import app

MAX_PAGE_SIZE = 10000
CLAN_LIST = 'clan_list LEFT JOIN login AS leader ON clan_list.clan_leader_id = leader.id ' \
             + 'LEFT JOIN login AS founder ON clan_list.clan_founder_id = founder.id'

COUNT_MEMBERS = '(SELECT COUNT(0) FROM clan_members WHERE (clan_list.clan_id = clan_members.clan_id))'
SELECT_EXPRESSIONS = {
    'clan_id': 'clan_id',
    'status': 'status',
    'clan_name': 'clan_name',
    'clan_tag': 'clan_tag',
    'clan_leader_id': 'clan_leader_id',
    'clan_founder_id': 'clan_founder_id',
    'clan_desc': 'clan_desc',
    'create_date': 'create_date',
    'leader_name': 'leader.login',
    'founder_name': 'founder.login',
    'clan_members' : COUNT_MEMBERS
}

@app.route('/clans')
def clans():
    return fetch_data(ClanSchema(), CLAN_LIST, SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request)
