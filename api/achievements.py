from flask import request
from api import *
from api.oauth import current_user


@app.route('/achievements')
def achievements_list():
    with db.connection.cursor(db.pymysql.cursors.DictCursor) as cursor:
        cursor.execute('''SELECT
                         id,
                         name,
                         description,
                         type,
                         total_steps,
                         revealed_icon_url,
                         unlocked_icon_url,
                         initial_state,
                         experience_points
                       FROM achievement_definitions''')

    return flask.jsonify(items=cursor.fetchall())


@app.route('/achievements/<achievement_id>')
def achievements_get(achievement_id):
    with db.connection.cursor(db.pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""SELECT
                         id,
                         name,
                         description,
                         type,
                         total_steps,
                         revealed_icon_url,
                         unlocked_icon_url,
                         initial_state,
                         experience_points
                       FROM achievement_definitions
                       WHERE id = '{0}'""".format(achievement_id))

    return cursor.fetchone()


@app.route('/achievements/<achievement_id>/increment', methods=['POST'])
def achievements_increment(achievement_id):
    achievement = achievements_get(achievement_id)
    current_player_id = current_user()
    steps_to_increment = request.args.get('steps', 1)

    with db.connection.cursor(db.pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""SELECT
                            current_steps,
                            state
                        FROM player_achievements
                        WHERE achievement_id = %s AND player_id = %s""",
                       (achievement_id, current_player_id))

    player_achievement = cursor.fetchone()

    new_current_steps = steps_to_increment
    new_state = 'REVEALED'
    newly_unlocked = False

    if player_achievement:
        new_current_steps += player_achievement['current_steps']

    if new_current_steps >= achievement['total_steps']:
        new_state = 'UNLOCKED'
        new_current_steps = achievement['total_steps']

        if player_achievement:
            newly_unlocked = player_achievement['state'] != 'UNLOCKED'

    with db.connection.cursor(db.pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""INSERT INTO player_achievements (player_id, achievement_id, current_steps, state)
                        VALUES
                            (%(player_id)s, %(achievement_id)s, %(current_steps)s, %(state)s)
                        ON DUPLICATE KEY UPDATE
                            current_steps = VALUES(current_steps),
                            state = VALUES(state)""",
                       {
                           'player_id': current_player_id,
                           'achievement_id': achievement_id,
                           'current_steps': new_current_steps,
                           'state': new_state,
                       })

    return {'current_steps': new_current_steps, 'newly_unlocked': newly_unlocked}


@app.route('/achievements/player/<int:player_id>')
def achievements_list_player(player_id):
    with db.connection.cursor(db.pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""SELECT
                            achievement_id,
                            current_steps,
                            state,
                            create_time,
                            update_time
                        FROM player_achievements
                        WHERE player_id = '%s'""" % player_id)

    return flask.jsonify(items=cursor.fetchall())
