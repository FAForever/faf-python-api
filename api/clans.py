import faf.db as db

from faf.api import ClanSchema
from flask import request
from api.query_commons import fetch_data
from api import app

MAX_PAGE_SIZE = 10000

SELECT_EXPRESSIONS = {
    'clan_id': 'clan_id',
    'status': 'status',
    'clan_name': 'clan_name',
    'clan_tag': 'clan_tag',
    'clan_leader_id': 'clan_leader_id',
    'clan_founder_id': 'clan_founder_id',
    'clan_desc': 'clan_desc',
    'create_date': 'create_date'
}


"""CREATE 
    ALGORITHM = UNDEFINED 
    DEFINER = `root`@`localhost` 
    SQL SECURITY DEFINER
VIEW `clans` AS
    SELECT 
        `clan_list`.`clan_id` AS `clan_id`,
        `clan_list`.`status` AS `status`,
        `clan_list`.`clan_name` AS `clan_name`,
        `clan_list`.`clan_tag` AS `clan_tag`,
        `clan_list`.`clan_leader_id` AS `clan_leader_id`,
        `clan_list`.`clan_founder_id` AS `clan_founder_id`,
        `clan_list`.`clan_desc` AS `clan_desc`,
        `clan_list`.`create_date` AS `create_date`,
        `leader`.`login` AS `leader_name`,
        `founder`.`login` AS `founder_name`,
        (SELECT 
                COUNT(0)
            FROM
                `clan_members`
            WHERE
                (`clan_list`.`clan_id` = `clan_members`.`clan_id`)) AS `member_count`
    FROM
        ((`clan_list`
        LEFT JOIN `login` `leader` ON ((`clan_list`.`clan_leader_id` = `leader`.`id`)))
        LEFT JOIN `login` `founder` ON ((`clan_list`.`clan_founder_id` = `founder`.`id`)))"""

@app.route('/clans')
def clans():
    return fetch_data(ClanSchema(), 'clan_list', SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request)
