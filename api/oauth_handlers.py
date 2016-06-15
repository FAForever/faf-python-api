from datetime import datetime, timedelta

from flask_login import current_user
from flask_oauthlib.contrib.cache import Cache

from api import *
from api.oauth_client import OAuthClient
from api.oauth_token import OAuthToken

cache = Cache(app, 'OAUTH2')


@oauth.clientgetter
def get_client(client_id):
    return OAuthClient.get(client_id)


@oauth.tokengetter
def get_token(access_token=None, refresh_token=None):
    return OAuthToken.get(access_token=access_token, refresh_token=refresh_token)


@oauth.tokensetter
def set_token(token, request, *args, **kwargs):
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
