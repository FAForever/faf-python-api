from flask import request

from api import *

import faf.db as db

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
                        AND desc_def.region = 'US'"""


@app.route('/achievements')
def achievements_list():
    """Lists all achievement definitions.

    HTTP Parameters::

        language    string  The preferred language to use for strings returned by this method
        region      string  The preferred region to use for strings returned by this method

    :return:
        If successful, this method returns a response body with the following structure::

            {
              "updated_achievements": [
                {
                  "id": string,
                  "name": string,
                  "description": string,
                  "type": string,
                  "total_steps": integer,
                  "initial_state": string,
                  "experience_points": integer,
                  "revealed_icon_url": string,
                  "unlocked_icon_url": string
                }
              ]
            }
    """
    language = request.args.get('language', 'en')
    region = request.args.get('region', 'US')

    with db.connection:
        cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
        cursor.execute(SELECT_ACHIEVEMENTS_QUERY + " ORDER BY `order` ASC",
                       {
                           'language': language,
                           'region': region
                       })

        return flask.jsonify(items=cursor.fetchall())


@app.route('/achievements/<achievement_id>')
def achievements_get(achievement_id):
    """Gets an achievement definition.

    HTTP Parameters::

        language    string  The preferred language to use for strings returned by this method
        region      string  The preferred region to use for strings returned by this method

    :param achievement_id: ID of the achievement to get

    :return:
        If successful, this method returns a response body with the following structure::

            {
              "id": string,
              "name": string,
              "description": string,
              "type": string,
              "total_steps": integer,
              "initial_state": string,
              "experience_points": integer,
              "revealed_icon_url": string,
              "unlocked_icon_url": string
            }
    """
    language = request.args.get('language', 'en')
    region = request.args.get('region', 'US')

    with db.connection:
        cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
        cursor.execute(SELECT_ACHIEVEMENTS_QUERY + "WHERE ach.id = %(achievement_id)s",
                       {
                           'language': language,
                           'region': region,
                           'achievement_id': achievement_id
                       })

        return cursor.fetchone()


@app.route('/achievements/<achievement_id>/increment', methods=['POST'])
def achievements_increment(achievement_id):
    """Increments the steps of the achievement with the given ID for the currently authenticated player.

    HTTP Parameters::

        player_id    integer ID of the player to increment the achievement for
        steps        string  The number of steps to increment

    :param achievement_id: ID of the achievement to increment

    :return:
        If successful, this method returns a response body with the following structure::

            {
              "current_steps": integer,
              "current_state": string,
              "newly_unlocked": boolean,
            }
    """
    # FIXME get player ID from OAuth session
    player_id = int(request.form.get('player_id'))
    steps = int(request.form.get('steps', 1))

    return flask.jsonify(increment_achievement(achievement_id, player_id, steps))


@app.route('/achievements/<achievement_id>/setStepsAtLeast', methods=['POST'])
def achievements_set_steps_at_least(achievement_id):
    """Sets the steps of an achievement. If the steps parameter is less than the current number of steps
     that the player already gained for the achievement, the achievement is not modified.
     This function is NOT an endpoint."""
    # FIXME get player ID from OAuth session
    player_id = int(request.form.get('player_id'))
    steps = int(request.form.get('steps', 1))

    return flask.jsonify(set_steps_at_least(achievement_id, player_id, steps))


@app.route('/achievements/<achievement_id>/unlock', methods=['POST'])
def achievements_unlock(achievement_id):
    """Unlocks an achievement for the currently authenticated player.

    HTTP Parameters::

        player_id    integer ID of the player to unlock the achievement for

    :param achievement_id: ID of the achievement to unlock

    :return:
        If successful, this method returns a response body with the following structure::

            {
              "newly_unlocked": boolean,
            }
    """
    # FIXME get player ID from OAuth session
    player_id = int(request.form.get('player_id'))

    return flask.jsonify(unlock_achievement(achievement_id, player_id))


@app.route('/achievements/<achievement_id>/reveal', methods=['POST'])
def achievements_reveal(achievement_id):
    """Reveals an achievement for the currently authenticated player.

    HTTP Parameters::

        player_id    integer ID of the player to reveal the achievement for

    :param achievement_id: ID of the achievement to reveal

    :return:
        If successful, this method returns a response body with the following structure::

            {
              "current_state": string,
            }
    """
    # FIXME get player ID from OAuth session
    player_id = int(request.form.get('player_id'))

    return flask.jsonify(reveal_achievement(achievement_id, player_id))


@app.route('/achievements/updateMultiple', methods=['POST'])
def achievements_update_multiple():
    """Updates multiple achievements for the currently authenticated player.

    HTTP Body:
        In the request body, supply data with the following structure::

            {
              "player_id": integer,
              "updates": [
                "achievement_id": string,
                "update_type": string,
                "steps": integer
              ]
            }

        ``updateType`` being one of "REVEAL", "INCREMENT" or "UNLOCK"

    :return:
        If successful, this method returns a response body with the following structure::

            {
              "updated_achievements": [
                "achievement_id": string,
                "current_state": string,
                "current_steps": integer,
                "newly_unlocked": boolean,
              ],
            }
    """
    # FIXME get player ID from OAuth session
    player_id = request.json['player_id']

    updates = request.json['updates']

    result = dict(updated_achievements=[])

    for update in updates:
        achievement_id = update['achievement_id']
        update_type = update['update_type']

        update_result = dict(achievement_id=achievement_id)

        if update_type == 'REVEAL':
            reveal_result = reveal_achievement(achievement_id, player_id)
            update_result['current_state'] = reveal_result['current_state']
            update_result['current_state'] = 'REVEALED'
        elif update_type == 'UNLOCK':
            unlock_result = unlock_achievement(achievement_id, player_id)
            update_result['newly_unlocked'] = unlock_result['newly_unlocked']
            update_result['current_state'] = 'UNLOCKED'
        elif update_type == 'INCREMENT':
            increment_result = increment_achievement(achievement_id, player_id, update['steps'])
            update_result['current_steps'] = increment_result['current_steps']
            update_result['current_state'] = increment_result['current_state']
            update_result['newly_unlocked'] = increment_result['newly_unlocked']
        elif update_type == 'SET_STEPS_AT_LEAST':
            set_steps_at_least_result = set_steps_at_least(achievement_id, player_id, update['steps'])
            update_result['current_steps'] = set_steps_at_least_result['current_steps']
            update_result['current_state'] = set_steps_at_least_result['current_state']
            update_result['newly_unlocked'] = set_steps_at_least_result['newly_unlocked']

        result['updated_achievements'].append(update_result)

    return result


@app.route('/players/<int:player_id>/achievements')
def achievements_list_player(player_id):
    """Lists the progress of achievements for a player.

    :param player_id: ID of the player.

    :return:
        If successful, this method returns a response body with the following structure::

            {
              "items": [
                {
                  "achievement_id": string,
                  "state": string,
                  "current_steps": integer,
                  "create_time": long,
                  "update_time": long
                }
              ]
            }
    """
    with db.connection:
        cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
        cursor.execute("""SELECT
                            achievement_id,
                            current_steps,
                            state,
                            UNIX_TIMESTAMP(create_time) as create_time,
                            UNIX_TIMESTAMP(update_time) as update_time
                        FROM player_achievements
                        WHERE player_id = '%s'""" % player_id)

        return flask.jsonify(items=cursor.fetchall())


def increment_achievement(achievement_id, player_id, steps):
    steps_function = lambda current_steps, new_steps: current_steps + new_steps
    return update_steps(achievement_id, player_id, steps, steps_function)


def set_steps_at_least(achievement_id, player_id, steps):
    steps_function = lambda current_steps, new_steps: max(current_steps, new_steps)
    return update_steps(achievement_id, player_id, steps, steps_function)


def update_steps(achievement_id, player_id, steps, steps_function):
    """Increments the steps of an achievement. This function is NOT an endpoint.

    :param achievement_id: ID of the achievement to increment
    :param player_id: ID of the player to increment the achievement for
    :param steps: The number of steps to increment
    :param steps_function: The function to use to calculate the new steps value. Two parameters are passed; the current
    step count and the parameter ``steps``

    :return:
        If successful, this method returns a dictionary with the following structure::

            {
              "current_steps": integer,
              "current_state": string,
              "newly_unlocked": boolean,
            }
    """
    achievement = achievements_get(achievement_id)

    with db.connection:
        cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
        cursor.execute("""SELECT
                            current_steps,
                            state
                        FROM player_achievements
                        WHERE achievement_id = %s AND player_id = %s""",
                       (achievement_id, player_id))

        player_achievement = cursor.fetchone()

        new_state = 'REVEALED'
        newly_unlocked = False

        current_steps = player_achievement['current_steps'] if player_achievement else 0
        new_current_steps = steps_function(current_steps, steps)

        if new_current_steps >= achievement['total_steps']:
            new_state = 'UNLOCKED'
            new_current_steps = achievement['total_steps']
            newly_unlocked = player_achievement['state'] != 'UNLOCKED' if player_achievement else True

        cursor.execute("""INSERT INTO player_achievements (player_id, achievement_id, current_steps, state)
                        VALUES
                            (%(player_id)s, %(achievement_id)s, %(current_steps)s, %(state)s)
                        ON DUPLICATE KEY UPDATE
                            current_steps = VALUES(current_steps),
                            state = VALUES(state)""",
                       {
                           'player_id': player_id,
                           'achievement_id': achievement_id,
                           'current_steps': new_current_steps,
                           'state': new_state,
                       })

    return dict(current_steps=new_current_steps, current_state=new_state, newly_unlocked=newly_unlocked)


def unlock_achievement(achievement_id, player_id):
    """Unlocks a standard achievement. This function is NOT an endpoint.

    :param achievement_id: ID of the achievement to unlock
    :param player_id: ID of the player to unlock the achievement for

    :return:
        If successful, this method returns a dictionary with the following structure::

            {
              "newly_unlocked": boolean,
            }
    """
    newly_unlocked = False

    with db.connection:
        cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)

        cursor.execute('SELECT type FROM achievement_definitions WHERE id = %s', achievement_id)
        achievement = cursor.fetchone()
        if achievement['type'] != 'STANDARD':
            raise InvalidUsage('Only standard achievements can be unlocked directly', status_code=400)

        cursor.execute("""SELECT
                            state
                        FROM player_achievements
                        WHERE achievement_id = %s AND player_id = %s""",
                       (achievement_id, player_id))

        player_achievement = cursor.fetchone()

        new_state = 'UNLOCKED'
        newly_unlocked = not player_achievement or player_achievement['state'] != 'UNLOCKED'

        cursor.execute("""INSERT INTO player_achievements (player_id, achievement_id, state)
                        VALUES
                            (%(player_id)s, %(achievement_id)s, %(state)s)
                        ON DUPLICATE KEY UPDATE
                            state = VALUES(state)""",
                       {
                           'player_id': player_id,
                           'achievement_id': achievement_id,
                           'state': new_state,
                       })

    return dict(newly_unlocked=newly_unlocked)


def reveal_achievement(achievement_id, player_id):
    """Reveals an achievement.

    :param achievement_id: ID of the achievement to unlock
    :param player_id: ID of the player to reveal the achievement for

    :return:
        If successful, this method returns a response body with the following structure::

            {
              "current_state": string,
            }
    """
    with db.connection:
        cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
        cursor.execute("""SELECT
                            state
                        FROM player_achievements
                        WHERE achievement_id = %s AND player_id = %s""",
                       (achievement_id, player_id))

        player_achievement = cursor.fetchone()

        new_state = player_achievement['state'] if player_achievement else 'REVEALED'

        cursor.execute("""INSERT INTO player_achievements (player_id, achievement_id, state)
                        VALUES
                            (%(player_id)s, %(achievement_id)s, %(state)s)
                        ON DUPLICATE KEY UPDATE
                            state = VALUES(state)""",
                       {
                           'player_id': player_id,
                           'achievement_id': achievement_id,
                           'state': new_state,
                       })

    return dict(current_state=new_state)
