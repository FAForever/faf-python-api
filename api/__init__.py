"""
Forged Alliance Forever API project

Distributed under GPLv3, see license.txt
"""
__version__ = '0.1'
__author__ = 'Chris Kitching, Michael Søndergaard, Vytautas Mickus'
__contact__ = 'admin@faforever.com'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (c) 2011-2015 ' + __author__

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

import db

def api_init():
    """
    Initializes flask. Call _after_ setting flask config.
    """
    db.init_db(app.config)
    app.github = github.make_session(app.config['GITHUB_USER'],
                                     app.config['GITHUB_TOKEN'])

# ======== Import (initialize) oauth2 handlers =====
import api.oauth


# ======== Import (initialize) routes =========
import api.deploy
import api.auth
import api.avatars
import api.games
import api.mods
import api.github
