"""
Forged Alliance Forever API project

Distributed under GPLv3, see license.txt
"""
from flask_oauthlib.contrib.oauth2 import bind_cache_grant
from flask_login import LoginManager
from api.user import User

__version__ = '0.1'
__author__ = 'Chris Kitching, Michael Søndergaard, Vytautas Mickus, Michel Jung'
__contact__ = 'admin@faforever.com'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (c) 2011-2015 ' + __author__

import sys

if sys.version_info.major != 3:
    raise RuntimeError(
        "FAForever API requires python 3.\n")

from flask import Flask, session, jsonify
from flask_oauthlib.provider import OAuth2Provider


class InvalidUsage(Exception):
    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        self.status_code = status_code or 400
        self.payload = payload

    def to_dict(self):
        return {
            **(self.payload or {}),
            'message': self.message
        }


# ======== Init Flask ==========

app = Flask('api')
login_manager = LoginManager()
login_manager.init_app(app)

_make_response = app.make_response


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    response.headers['content-type'] = 'application/vnd.api+json'
    return response


def make_response_json(rv):
    """
    Override the flask make_response function to default to application/json
    for lists and dictionaries.
    """
    if isinstance(rv, app.response_class):
        return rv
    if isinstance(rv, dict):
        response = jsonify(rv)
        response.headers['content-type'] = 'application/vnd.api+json'
        return response
    elif isinstance(rv, tuple):
        values = dict(zip(['response', 'status', 'headers'], rv))
        response, status, headers = values.get('response', ''), values.get('status', 200), values.get('headers', [])
        if isinstance(response, dict):
            response = jsonify(values['response'])
        else:
            response = _make_response(response)
        response.status_code = values.get('status', 200)
        response.headers = values.get('headers', response.headers)
        response.headers['content-type'] = 'application/vnd.api+json'
        return response
    else:
        return _make_response(rv)


app.make_response = make_response_json

# ======== Init Database =======

import faf.db


def api_init():
    """
    Initializes flask. Call _after_ setting flask config.
    """
    faf.db.init_db(app.config)
    app.github = github.make_session(app.config['GITHUB_USER'],
                                     app.config['GITHUB_TOKEN'])

    app.secret_key = app.config['FLASK_LOGIN_SECRET_KEY']


# ======== Init OAuth =======


def get_current_user():
    if 'user_id' not in session:
        return None

    return User.get_by_id(session['user_id'])


oauth = OAuth2Provider(app)
app.config.update({'OAUTH2_CACHE_TYPE': 'simple'})

bind_cache_grant(app, oauth, get_current_user)

# ======== Import (initialize) oauth2 handlers =====
import api.oauth
# ======== Import (initialize) routes =========
import api.deploy
import api.auth
import api.avatars
import api.games
import api.mods
import api.maps
import api.github
import api.oauth_client
import api.oauth_token
