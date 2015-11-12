from flask import request
from flask_jwt import jwt_required, current_identity

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

    return dict(items=cursor.fetchall())


@app.route('/events/recordMultiple', methods=['POST'])
@oauth.require_oauth('write_events')
def events_record_multiple():
    """Records multiple events for the currently authenticated player.

    HTTP Body:
        In the request body, supply data with the following structure::

            {
              "updates": [
                {
                  "event_id": string,
                  "count": long
                }
              ]
            }

    :return:
        If successful, this method returns a response body with the following structure::

            {
              "updated_events": [
                {
                  "event_id": string,
                  "count": long
                }
              ],
            }
    """
    return record_multiple(request.oauth.user.id, request.json['updates'])


@app.route('/jwt/events/recordMultiple', methods=['POST'])
@jwt_required()
def jwt_events_record_multiple():
    return record_multiple(current_identity.id, request.json['updates'])


@app.route('/events/<event_id>/record', methods=['POST'])
@oauth.require_oauth('write_events')
def events_record(event_id):
    return record_event(event_id, request.oauth.user.id, request.values.get('count', 1))


def record_event(event_id, player_id, count):
    """Records an event. This function is NOT an endpoint.

    :return:
        If successful, this method returns a dictionary with the following structure::

            {
              "count": long
            }
    """

    with db.connection:
        cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
        cursor.execute("""INSERT INTO player_events (player_id, event_id, count)
                        VALUES
                            (%(player_id)s, %(event_id)s, %(count)s)
                        ON DUPLICATE KEY UPDATE
                            count = count + VALUES(count)""",
                       {
                           'player_id': player_id,
                           'event_id': event_id,
                           'count': count,
                       })

        cursor.execute("""SELECT
                            count
                        FROM player_events
                        WHERE event_id = %s AND player_id = %s""",
                       (event_id, player_id))

        return cursor.fetchone()


def record_multiple(player_id, updates):
    result = {'updated_events': []}

    for update in updates:
        event_id = update['event_id']
        count = update['count']

        update_result = dict(event_id=event_id)
        update_result['count'] = record_event(event_id, player_id, count)['count']

        result['updated_events'].append(update_result)

    return result
