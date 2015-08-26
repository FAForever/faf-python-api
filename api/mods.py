import db

from api import app


@app.route('/mods')
def get_mods():
    with db.connection.cursor() as cursor:
        cursor.execute('SELECT name from table_mod')
        mods = []
        while cursor.rowcount > 1:
            mods.append(cursor.fetchone())
    return {
                'data': [
                    {
                        'type': 'mods',
                        'id': 1
                    }
                ]
            }
