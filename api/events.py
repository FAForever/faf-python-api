from api import *


@app.route('/events')
def events_list():
    with db.connection.cursor(db.pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT id, name, image_url, type from event_definitions")

    return flask.jsonify(data=cursor.fetchall())
