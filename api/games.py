
from api import *

@app.route('/games/<int:id>')
@app.route('/games/<int:id>/<resource>')
def games_get(id, resource='info'):

    if resource == 'info':
        return dict(
            id=1,
            Title = 'Test',
            GameState = 'Pre-Lobby',
            PlayerOption = dict(),
            GameOption = {},
            GameMods = [],
            Host = dict(username='Eximius', ip='127.0.0.1', port=1234)
        )

@app.route('/games/current')
def games_current():
    return dict(
        games=[games_get(0)]
    )