from flask import request
import flask
from api import *

import faf.db as db

SELECT_EVENTS_QUERY = """SELECT
                            events.id,
                            events.image_url,
                            events.type,
                            COALESCE(name_langReg.value, name_lang.value, name_def.value) as name
                        FROM event_definitions events
                        LEFT OUTER JOIN messages name_langReg
                            ON events.name_key = name_langReg.key
                                AND name_langReg.language = %(language)s
                                AND name_langReg.region = %(region)s
                        LEFT OUTER JOIN messages name_lang
                            ON events.name_key = name_lang.key
                                AND name_lang.language = %(language)s
                        LEFT OUTER JOIN messages name_def
                            ON events.name_key = name_def.key
                                AND name_def.language = 'en'
                                AND name_def.region = 'US'"""


@app.route('/events')
def events_list():
    """Lists all event definitions.

    HTTP Parameters::

        language    string  The preferred language to use for strings returned by this method
        region      string  The preferred region to use for strings returned by this method

    :return:
        If successful, this method returns a response body with the following structure::

            {
              "items": [
                {
                  "id": string,
                  "name": string,
                  "type": string,
                  "image_url": string
                }
              ]
            }
    """
    language = request.args.get('language', 'en')
    region = request.args.get('region', 'US')

    with db.connection:
        cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
        cursor.execute(SELECT_EVENTS_QUERY + " ORDER BY id ASC",
                       {
                           'language': language,
                           'region': region,
                       })

    return flask.jsonify(items=cursor.fetchall())


@app.route('/events/recordMultiple', methods=['POST'])
def events_record_multiple():
    """Records multiple events for the currently authenticated player.

    HTTP Parameters::

        player_id    integer ID of the player to update the achievements for

    HTTP Body:
        In the request body, supply data with the following structure::

            {
              "updates": [
                "event_id": string,
                "update_count": long,
              ]
            }

    :return:
        If successful, this method returns a response body with the following structure::

            {
              "updated_events": [
                {
                  "event_id": string,
                  "count": long,
                }
              ],
            }
    """
    # FIXME get player ID from OAuth session
    player_id = request.json['player_id']

    updates = request.json['updates']

    result = {'updated_events': []}

    for update in updates:
        event_id = update['event_id']
        update_count = update['update_count']

        update_result = record_event(event_id, player_id, update_count)

        result['updated_events'].append(update_result)

    return result


def record_event(event_id, player_id, update_count):
    """Records an event. This function is NOT an endpoint.

    :return:
        If successful, this method returns a dictionary with the following structure::

            {
              "event_id": string,
              "count": long,
            }
    """

    with db.connection:
        cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
        cursor.execute("""INSERT INTO player_events (player_id, event_id, count)
                        VALUES
                            (%(player_id)s, %(event_id)s, %(update_count)s)
                        ON DUPLICATE KEY UPDATE
                            count = count + VALUES(count)""",
                       {
                           'player_id': player_id,
                           'event_id': event_id,
                           'update_count': update_count,
                       })

        cursor.execute("""SELECT
                            event_id,
                            count
                        FROM player_events
                        WHERE event_id = %s AND player_id = %s""",
                       (event_id, player_id))

        return cursor.fetchone()
