"""
Holds the authorization url routes
"""
import base64
import json
from functools import wraps
from hashlib import sha256
from typing import Union
from urllib.parse import urlparse
import re

import jwt
from flask import redirect, url_for, render_template, abort, g
from flask_jwt import JWTError
from flask_login import login_user

from api.error import ErrorCode, Error
from api.oauth_handlers import *
from api import flask_jwt


def _urlsafe_b64decode(b64string: Union[str, bytes]):
    if isinstance(b64string, str):
        b64string = b64string.encode('utf-8')
    padded = b64string + b'=' * (4 - len(b64string) % 4)
    return base64.urlsafe_b64decode(padded)


def require_login(function):
    @wraps(function)
    def decorated_function(*args, **kwargs):
        if current_user is None or not current_user.is_authenticated:
            return redirect(url_for('login', next=request.url))
        return function(*args, **kwargs)

    return decorated_function


@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(int(user_id))


@app.route('/jwt/auth', methods=['GET', 'POST'])
def jwt_auth():
    assertion = request.values.get('assertion')
    segments = assertion.split('.')

    payload = json.loads(_urlsafe_b64decode(segments[1]).decode('utf-8'))
    service_account = JwtUser.get(payload['iss'])

    if not service_account:
        raise JWTError('Bad Request', 'Invalid service account')

    jwt.decode(assertion, service_account.public_key, algorithms=['RS256'], options=dict(verify_aud=False))

    identity = User.get_by_id(payload['sub'])

    access_token = flask_jwt.jwt_encode_callback(identity)
    return flask_jwt.auth_response_callback(access_token, identity)


@app.route('/oauth/authorize', methods=['GET', 'POST'])
@require_login
@oauth.authorize_handler
def authorize(*args, **kwargs):

    if request.method == 'GET':
        kwargs['client'] = kwargs['request'].client
        return render_template('authorize.html', **kwargs)

    confirm = request.form.get('allow', 'no')
    return confirm == 'yes'


@app.route('/oauth/token', methods=['POST'])
@oauth.token_handler
def access_token():
    """
    The implementation of this endpoint is handled by the @oauth.token_handler function

    Function left blank intentionally
    :return: None
    """
    return None

@app.route('/oauth/revoke')
@oauth.revoke_handler
def oauth_revoke():
    pass

@app.route('/login', methods=['GET', 'POST'])
def login(*args, **kwargs):
    if request.method == 'GET':
        kwargs['next'] = request.values.get('next')
        return render_template('login.html', **kwargs)

    username = request.form.get('username')
    # TODO implement salt as soon as available
    password = request.form.get('password')

    is_banned, ban_reason = User.is_banned(username)
    if is_banned:
        raise ApiException([Error(ErrorCode.LOGIN_DENIED_BANNED, ban_reason)])

    user = User.get_by_username(username)

    hashed_password = password if len(password) == 64 else sha256(password.encode()).hexdigest()

    if user is None or user.password != hashed_password:
        kwargs['next'] = request.values.get('next')
        return render_template('login.html', **kwargs)

    login_user(user, remember=True)

    redirect_url = request.values.get('next')

    if not redirect_url_is_valid(redirect_url):
        return abort(400)

    return redirect(redirect_url)


VALIDATE_DOMAIN_REGEX = re.compile("^(localhost|(.*\.)?faforever.com):?(?:[0-9]*)?$")


def redirect_url_is_valid(redirect_url):
    if not redirect_url:
        return False
    parsed = urlparse(redirect_url)
    return VALIDATE_DOMAIN_REGEX.match(parsed.netloc)
