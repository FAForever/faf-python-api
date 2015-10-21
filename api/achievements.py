from flask import request
import flask
from api import *
from api.oauth import current_user

SELECT_ACHIEVEMENTS_QUERY = """SELECT
                    ach.id,
                    ach.type,
                    ach.total_steps,
                    ach.revealed_icon_url,
                    ach.unlocked_icon_url,
                    ach.initial_state,
                    ach.experience_points,
                    COALESCE(name_langReg.value, name_lang.value, name_def.value) as name,
                    COALESCE(desc_langReg.value, desc_lang.value, desc_def.value) as description
                FROM achievement_definitions ach
                LEFT OUTER JOIN messages name_langReg
                    ON ach.name_key = name_langReg.key
                        AND name_langReg.language = %(language)s
                        AND name_langReg.region = %(region)s
                LEFT OUTER JOIN messages name_lang
                    ON ach.name_key = name_lang.key
                        AND name_lang.language = %(language)s
                LEFT OUTER JOIN messages name_def
                    ON ach.name_key = name_def.key
                        AND name_def.language = 'en'
                        AND name_def.region = 'US'
                LEFT OUTER JOIN messages desc_langReg
                    ON ach.description_key = desc_langReg.key
                        AND desc_langReg.language = %(language)s
                        AND desc_langReg.region = %(region)s
                LEFT OUTER JOIN messages desc_lang
                    ON ach.description_key = desc_lang.key
                        AND desc_lang.language = %(language)s
                LEFT OUTER JOIN messages desc_def
                    ON ach.description_key = desc_def.key
                        AND desc_def.language = 'en'
                        AND desc_def.region = 'US'""";


@app.route('/achievements')
def achievements_list():
    language = request.args.get('language', 'en')
    region = request.args.get('region', 'US')

    with db.connection.cursor(db.pymysql.cursors.DictCursor) as cursor:
        cursor.execute(SELECT_ACHIEVEMENTS_QUERY,
                       {
                           'language': language,
                           'region': region
                       })

    return flask.jsonify(items=cursor.fetchall())


@app.route('/achievements/<achievement_id>')
def achievements_get(achievement_id):
    language = request.args.get('language', 'en')
    region = request.args.get('region', 'US')

    with db.connection.cursor(db.pymysql.cursors.DictCursor) as cursor:
        cursor.execute(SELECT_ACHIEVEMENTS_QUERY + "WHERE ach.id = %(achievement_id)s",
                       {
                           'language': language,
                           'region': region,
                           'achievement_id': achievement_id
                       })

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

    db.connection.commit()
    cursor.close()

    return {'current_steps': new_current_steps, 'current_state': new_state, 'newly_unlocked': newly_unlocked}


@app.route('/achievements/<achievement_id>/unlock', methods=['POST'])
def achievements_unlock(achievement_id):
    # FIXME get player ID from OAuth session
    current_player_id = 1

    with db.connection.cursor(db.pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""SELECT
                            state
                        FROM player_achievements
                        WHERE achievement_id = %s AND player_id = %s""",
                       (achievement_id, current_player_id))

    player_achievement = cursor.fetchone()

    new_state = 'UNLOCKED'
    newly_unlocked = not player_achievement or player_achievement['state'] != 'UNLOCKED'

    with db.connection.cursor(db.pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""INSERT INTO player_achievements (player_id, achievement_id, state)
                        VALUES
                            (%(player_id)s, %(achievement_id)s, %(state)s)
                        ON DUPLICATE KEY UPDATE
                            state = VALUES(state)""",
                       {
                           'player_id': current_player_id,
                           'achievement_id': achievement_id,
                           'state': new_state,
                       })

    db.connection.commit()
    cursor.close()

    return {'newly_unlocked': newly_unlocked}


@app.route('/achievements/<achievement_id>/reveal', methods=['POST'])
def achievements_reveal(achievement_id):
    current_player_id = current_user()

    with db.connection.cursor(db.pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""SELECT
                            state
                        FROM player_achievements
                        WHERE achievement_id = %s AND player_id = %s""",
                       (achievement_id, current_player_id))

    player_achievement = cursor.fetchone()

    new_state = player_achievement['state'] if player_achievement else 'REVEALED'

    with db.connection.cursor(db.pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""INSERT INTO player_achievements (player_id, achievement_id, state)
                        VALUES
                            (%(player_id)s, %(achievement_id)s, %(state)s)
                        ON DUPLICATE KEY UPDATE
                            state = VALUES(state)""",
                       {
                           'player_id': current_player_id,
                           'achievement_id': achievement_id,
                           'state': new_state,
                       })

    db.connection.commit()
    cursor.close()

    return {'current_state': new_state}


@app.route('/achievements/updateMultiple', methods=['POST'])
def achievements_update_multiple():
    updates = request.args.get('updates')

    result = {'updated_achievements': []}

    for update in updates:
        achievement_id = update['achievementId']
        update_type = update['updateType']

        update_result = {'achievement_id': achievement_id}

        if update_type == 'REVEAL':
            reveal_result = achievements_reveal(achievement_id)
            update_result['current_state'] = reveal_result['current_state']
            update_result['current_state'] = 'REVEALED'
        elif update_type == 'UNLOCK':
            unlock_result = achievements_unlock(achievement_id)
            update_result['newly_unlocked'] = unlock_result['newly_unlocked']
            update_result['current_state'] = 'UNLOCKED'
        elif update_type == 'INCREMENT':
            increment_result = achievements_increment(achievement_id)
            update_result['current_steps'] = increment_result['current_steps']
            update_result['current_state'] = increment_result['current_state']
            update_result['newly_unlocked'] = increment_result['newly_unlocked']

        result['updated_achievements'].append(update_result)

    return result


@app.route('/player/<int:player_id>/achievements')
def achievements_list_player(player_id):
    with db.connection.cursor(db.pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""SELECT
                            achievement_id,
                            current_steps,
                            state,
                            UNIX_TIMESTAMP(create_time) as create_time,
                            UNIX_TIMESTAMP(update_time) as update_time
                        FROM player_achievements
                        WHERE player_id = '%s'""" % player_id)

    return flask.jsonify(items=cursor.fetchall())
