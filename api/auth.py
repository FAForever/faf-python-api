"""
Holds the authorization url routes
"""
from functools import wraps
from hashlib import sha256
import re

from flask import request, redirect, url_for, render_template, abort, g
from flask_login import login_user, current_user

from api.oauth import *

VALID_REDIRECT_URL_PATTERN = re.compile("^https?://(?:localhost|.*?\.faforever.com)(?:[:/].*)?$")


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
        return render_template('login.html', **kwargs)

    username = request.form.get('username')
    # TODO implement salt as soon as available
    password = request.form.get('password').encode('utf-8')

    user = User.get_by_username(username)

    if user is None or user.password != sha256(password).hexdigest():
        return render_template('login.html', **kwargs)

    login_user(user, remember=True)

    redirect_url = request.form.get('next')

    if not redirect_url_is_valid(redirect_url):
        return abort(400)

    return redirect(redirect_url)


def redirect_url_is_valid(redirect_url):
    return redirect_url is not None and VALID_REDIRECT_URL_PATTERN.match(redirect_url) is not None

