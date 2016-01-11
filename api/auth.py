"""
Holds the authorization url routes
"""
import base64
import json
from functools import wraps
from hashlib import sha256
from urllib.parse import urlparse
import re

import jwt
from flask import request, redirect, url_for, render_template, abort, g
from flask_jwt import JWTError
from flask_login import login_user, current_user
from requests.packages.urllib3.packages import six
from api.oauth_handlers import *
from api import flask_jwt


def _to_bytes(value, encoding='ascii'):
    """Converts a string value to bytes, if necessary.

    Unfortunately, ``six.b`` is insufficient for this task since in
    Python2 it does not modify ``unicode`` objects.

    Args:
        value: The string/bytes value to be converted.
        encoding: The encoding to use to convert unicode to bytes. Defaults
                  to "ascii", which will not allow any characters from ordinals
                  larger than 127. Other useful values are "latin-1", which
                  which will only allows byte ordinals (up to 255) and "utf-8",
                  which will encode any unicode that needs to be.

    Returns:
        The original value converted to bytes (if unicode) or as passed in
        if it started out as bytes.

    Raises:
        ValueError if the value could not be converted to bytes.
    """
    result = (value.encode(encoding)
              if isinstance(value, six.text_type) else value)
    if isinstance(result, six.binary_type):
        return result
    else:
        raise ValueError('%r could not be converted to bytes' % (value,))


def _urlsafe_b64decode(b64string):
    # Guard against unicode strings, which base64 can't handle.
    b64string = _to_bytes(b64string)
    padded = b64string + b'=' * (4 - len(b64string) % 4)
    return base64.urlsafe_b64decode(padded)


@app.before_request
def before_request():
    g.user = current_user


def require_login(function):
    @wraps(function)
    def decorated_function(*args, **kwargs):
        if g.user is None or not g.user.is_authenticated:
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
        client_id = kwargs.get('client_id')
        client = get_client(client_id)
        scopes = kwargs.get('scope')
        kwargs['client'] = client
        kwargs['user'] = current_user
        kwargs['scopes'] = scopes.split() if scopes else client.default_scopes;
        return render_template('authorize.html', **kwargs)

    return request.form.get('allow', None) is not None


@app.route('/oauth/token', methods=['POST'])
@oauth.token_handler
def access_token():
    """
    The implementation of this endpoint is handled by the @oauth.token_handler function

    Function left blank intentionally
    :return: None
    """
    return None


@app.route('/login', methods=['GET', 'POST'])
def login(*args, **kwargs):
    if request.method == 'GET':
        kwargs['next'] = request.values.get('next')
        return render_template('login.html', **kwargs)

    username = request.form.get('username')
    # TODO implement salt as soon as available
    password = request.form.get('password').encode('utf-8')

    user = User.get_by_username(username)

    hashed_password = password if len(password) == 64 else sha256(password).hexdigest()

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
