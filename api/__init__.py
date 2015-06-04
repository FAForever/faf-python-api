"""
Main file for the Flask application
"""

import sys

if sys.version_info.major != 3:
    raise RuntimeError(
        "FAForever API requires python 3.\n")

from flask import Flask, session
from flask_oauthlib.provider import OAuth2Provider

# ======== Init Flask ==========

app = Flask('api')
oauth = OAuth2Provider(app)

_make_response = app.make_response
def make_response_json(result):
    "Overrides the original make_response to emit json for python types"
    from flask import Response, json

    if isinstance(result,(int,bool,float,str,list,dict)):
        # Json response
        resp = Response(status=200,mimetype='application/json')

        resp.set_data(json.dumps(result))

        return resp
    else:
        return _make_response(result)

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
import api.auth
import api.avatars
import api.games
