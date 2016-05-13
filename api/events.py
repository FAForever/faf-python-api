from copy import copy
from faf.api import PlayerEventSchema
from faf.api.event_schema import EventSchema
from flask_jwt import jwt_required, current_identity
from api import *
import faf.db as db
from api.query_commons import fetch_data

MAX_PAGE_SIZE = 1000

EVENTS_TABLE = """event_definitions events
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

EVENTS_SELECT_EXPRESSIONS = {
    'id': 'events.id',
    'image_url': 'events.image_url',
    'type': 'events.type',
    'name': 'COALESCE(name_langReg.value, name_lang.value, name_def.value)'
}

PLAYER_EVENTS_SELECT_EXPRESSIONS = {
    'id': 'id',
    'player_id': 'player_id',
    'event_id': 'event_id',
    'count': 'count',
}


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

    return fetch_data(EventSchema(), EVENTS_TABLE, EVENTS_SELECT_EXPRESSIONS, MAX_PAGE_SIZE, request,
                      args={'language': language, 'region': region})


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


@app.route('/players/<int:player_id>/events')
@oauth.require_oauth('read_events')
def events_list_player(player_id):
    """Lists the events for a player.

    :param player_id: ID of the player.

    :return:
        If successful, this method returns a response body with the following structure::

            {
              "data": [
                {
                  "id": string,
                  "attributes": {
                      "event_id": string,
                      "count": integer,
                      "create_time": long,
                      "update_time": long
                  }
                }
              ]
            }
    """
    select_expressions = copy(PLAYER_EVENTS_SELECT_EXPRESSIONS)
    del select_expressions['player_id']

    where = 'player_id = %s'
    args = tuple([player_id])

    id_filter = request.values.get('filter[event_id]')
    if id_filter:
        ids = id_filter.split(',')
        where += ' AND event_id IN ({})'.format(','.join(['%s'] * len(ids)))
        args += tuple(ids)

    return fetch_data(PlayerEventSchema(), 'player_events', select_expressions,
                      MAX_PAGE_SIZE, request, where=where, args=args)


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
