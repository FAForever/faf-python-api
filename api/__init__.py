"""
Main file for the Flask application
"""

import sys
import flask

if sys.version_info.major != 3:
    raise RuntimeError(
        "FAForever API requires python 3.\n")

from flask import Flask, session, jsonify
from flask_oauthlib.provider import OAuth2Provider

# ======== Init Flask ==========

app = Flask('api')
oauth = OAuth2Provider(app)

_make_response = app.make_response
def make_response_json(rv):
    """
    Override the flask make_response function to default to application/json
    for lists and dictionaries.
    """
    if isinstance(rv, app.response_class):
        return rv
    if isinstance(rv, dict):
        return jsonify(rv)
    elif isinstance(rv, tuple):
        values = dict(zip(['response', 'status', 'headers'], rv))
        response, status, headers = values.get('response', ''), values.get('status', 200), values.get('headers', [])
        if isinstance(response, dict):
            response = jsonify(values['response'])
        else:
            response = _make_response(response)
        response.status_code = values.get('status', 200)
        response.headers = values.get('headers', response.headers)
        return response
    else:
        return _make_response(rv)

app.make_response = make_response_json

# ======== Init Database =======

from db.faf_orm import *
from playhouse.flask_utils import FlaskDB

flask_db = FlaskDB()

def api_init():
    """
    Initializes flask. Call _after_ setting flask config.
    """
    flask_db.init_app(app)
    faf_orm_init_db(flask_db.database)
    app.github = github.make_session(app.config['GITHUB_USER'],
                                     app.config['GITHUB_TOKEN'])

# ======== Import (initialize) oauth2 handlers =====
import api.oauth


# ======== Import (initialize) routes =========
import api.data
import api.deploy
import api.auth
import api.avatars
import api.games
import api.github
