import faf.db as db

from api import *

@app.route('/clans')
def clans_get():
    clans = []
    with db.connection.cursor(db.pymysql.cursors.DictCursor) as cursor:
        cursor.execute('SELECT * FROM clans WHERE status = 1')
        clans = cursor.fetchall()
    return { 'data': clans }

@app.route('/clan/<int:id>')
def clan_get(id):
    with db.connection.cursor(db.pymysql.cursors.DictCursor) as cursor:
        cursor.execute('SELECT * FROM clans WHERE clan_id = %s LIMIT 1', id)
        if cursor.rowcount == 1:
            clan_details = cursor.fetchall()
            cursor.execute('SELECT `player_id`, `login`.`login` `player_name`, `join_clan_date` '
                + 'FROM `clan_members` LEFT JOIN `login` ON `clan_members`.`player_id` = `login`.`id` '
                + 'WHERE `clan_id` = %s ' , id)
            return { 'clan_details': clan_details,
                     'members': cursor.fetchall() }
    return {}
