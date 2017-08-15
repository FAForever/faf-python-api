from datetime import datetime, timedelta
from hashlib import sha256

import flask_oauthlib
from flask_login import current_user

from api import *
from api.helpers import *
from api.oauth_client import OAuthClient
from api.oauth_token import OAuthToken

cache = flask_oauthlib.contrib.cache.Cache(app, 'OAUTH2')


@oauth.clientgetter
def get_client(client_id):
    return OAuthClient.get(client_id)

@oauth.usergetter
def get_user(username, password, client, request,
             *args, **kwargs):
    user = User.get_by_username(username)

    # only used for password grant, so check here that client is public
    if client.client_type != 'public':
        raise ApiException([Error(ErrorCode.AUTH_NOT_PUBLIC_CLIENT)])

    hashed_password = password if len(password) == 64 else sha256(password.encode()).hexdigest()
    if user is None or user.password != hashed_password:
        return None

    return user

@oauth.tokengetter
def get_token(access_token=None, refresh_token=None):
    return OAuthToken.get(access_token=access_token, refresh_token=refresh_token)


@oauth.tokensetter
def set_token(token, request, *args, **kwargs):
    # https://github.com/lepture/flask-oauthlib/issues/209
    user_id = request.user.id if hasattr(request.user, 'id') else current_user.id

    # make sure that every client has only one token connected to a user
    OAuthToken.delete(request.client.client_id, user_id)

    with faf.db.connection:
        expires_in = token.get('expires_in')
        expires = datetime.utcnow() + timedelta(seconds=expires_in)

        return OAuthToken.insert(
            access_token=token['access_token'],
            # TODO: Support refresh token?
            refresh_token=token.get('refresh_token', ''),
            token_type=token['token_type'],
            scope=token.scope,
            expires=expires,
            client_id=request.client.client_id,
            user_id=user_id
        )
