from faf.api.client.client_base import ApiException
from faf.api.history_schema import HistorySchema
from pymysql.cursors import DictCursor

from api import app
from api.error import Error, ErrorCode
from faf import db


@app.route('/players/<int:player_id>/ratings/<string:rating_type>/history')
def users_type_get_player_history(rating_type, player_id):
    """
        Gets a global or 1v1 player's rating history. Player must be active, played more than one ranked game, and must
        have statistics associated.

        **Example Request**:

        .. sourcecode:: http

           GET /leaderboards/1v1/781/history

        **Example Response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Vary: Accept
            Content-Type: text/javascript

            {
              "data": {
                "attributes": {
                  "history": {
                    "1469921413": [1026.62, 49.4094],
                    "1469989967": [1024.01, 49.4545],
                    "1470842200": [1020.65, 50.1963]
                  }
                },
                "id": "21447",
                "type": "leaderboard_history"
              }
            }

        :param rating_type: Gets statistics for "1v1" or "global" rating
        :type rating_type: 1v1 OR global
        :param player_id: Player ID
        :type player_id: int

        :status 200: No error

        """
    if rating_type == 'global':
        game_mod = 'faf'
    elif rating_type == '1v1':
        game_mod = 'ladder1v1'
    else:
        raise ApiException([Error(ErrorCode.QUERY_INVALID_RATING_TYPE, rating_type)])

    with db.connection:
        cursor = db.connection.cursor(DictCursor)
        cursor.execute("""SELECT
                              after_mean,
                              after_deviation,
                              UNIX_TIMESTAMP(scoreTime) as scoreTime
                            FROM game_player_stats
                              JOIN game_stats ON game_player_stats.gameId = game_stats.id
                              JOIN game_featuredMods ON game_stats.gameMod = game_featuredMods.id
                              JOIN login ON login.id = playerId
                            WHERE after_mean IS NOT NULL
                                  AND after_deviation IS NOT NULL
                                  AND scoreTime IS NOT NULL
                                  AND game_featuredMods.gamemod = %(game_mod)s
                                  AND game_player_stats.playerId = %(player_id)s
                            """,
                       {
                           'game_mod': game_mod,
                           'player_id': player_id
                       })

        result = cursor.fetchall()

    data = dict(id=player_id, history={})

    for item in result:
        data['history'][str(int(item['scoreTime']))] = [item['after_mean'], item['after_deviation']]

    return HistorySchema().dump(data, many=False).data
