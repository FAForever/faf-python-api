"""
Main file for the Flask application
"""

import sys
import flask

if sys.version_info.major != 3:
    raise RuntimeError(
        "FAForever API requires python 3.\n")

from flask import Flask, session
from flask_oauthlib.provider import OAuth2Provider

# ======== Init Flask ==========

app = Flask('api')
oauth = OAuth2Provider(app)

_make_response = app.make_response
def make_response_json(*args, **kwargs):
    """
    Override the flask make_response function to default to application/json
    for lists and dictionaries.
    """
    if len(args) == 1 and isinstance(args[0], (list, dict)):
        return flask.json.jsonify(*args, **kwargs)
    elif (len(args) == 2 and isinstance(args[0], (list, dict))
                         and isinstance(args[1], int)):
        response = flask.json.jsonify(*args[0])
        response.status_code = args[1]
        return response
    else:
        return _make_response(*args, **kwargs)

app.make_response = make_response_json

# ======== Init Database =======

from db.faf_orm import *
from playhouse.flask_utils import FlaskDB

flask_db = FlaskDB()

def api_init():
    "Initializes flask. Call _after_ setting flask config."
    flask_db.init_app(app)
    faf_orm_init_db(flask_db.database)

# ======== Import (initialize) oauth2 handlers =====
import api.oauth


# ======== Import (initialize) routes =========
import api.data
import api.deploy
import api.auth
import api.avatars
import api.games
