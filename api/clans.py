import db, pymysql

from api import *

@app.route('/clans')
def clans_get():
    clans = []
    with db.connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute('SELECT * FROM clan_list WHERE status = 1')
        clans = cursor.fetchall()

    return { 'data': clans }

@app.route('/clan/<int:id>')
def clan_get(id):
    with db.connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute('SELECT * FROM clan_list WHERE clan_id = %s LIMIT 1', id)
        if cursor.rowcount == 1:
            clan_details = cursor.fetchall()
            cursor.execute('SELECT `player_id`, `player_name`, `join_clan_date` '
                + 'FROM clan_members WHERE clan_id = %s', id)
            return { 'clan_details': clan_details,
                     'members': cursor.fetchall() }
    return {}

@app.route('/clan_members')
def clan_members_get():
    members = []
    with db.connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute('SELECT * FROM clan_members')
        members = cursor.fetchall()
        
    return { 'data': members }