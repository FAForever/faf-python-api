
from api import *

from datetime import datetime

# OAuth2 resource mapping
def current_user():
    try:
        if 'id' in session:
            uid = int(session['id'])
            return User.get(User.id == uid)
    except ValueError:
        pass
    return None

@oauth.usergetter
def user_get(username, password, client, *args, **kwargs):
    try:
        user = User.get(User.login == username)
        if user.password == password:
            return user
    except DoesNotExist:
        pass

@oauth.clientgetter
def load_client(client_id):
    return OAuthClient.get(OAuthClient.client_id == client_id)

@oauth.grantgetter
def load_grant(client_id, code):
    return OAuthToken.get(OAuthToken.client == client_id,
                                OAuthToken.code == code)

from datetime import timedelta
@oauth.grantsetter
def save_grant(client_id, code, request, *args, **kwargs):
    expires = datetime.utcnow() + timedelta(seconds=600)

    return OAuthToken.create(
        client_id=client_id,
        code = code['code'],
        redirect_uri = request.redirect_uri,
        _scopes=' '.join(request.scopes),
        user=current_user(),
        expires=expires
    )

@oauth.tokengetter
def load_token(access_token=None, refresh_token=None):
    if access_token:
        return OAuthToken.get(OAuthToken.access_token == access_token)

    if refresh_token:
        return OAuthToken.get(OAuthToken.refresh_token == refresh_token)

@oauth.tokensetter
def save_token(token, request, *args, **kwargs):
    with db.transaction():
        # make sure that every client has only one token connected to a user
        OAuthToken.delete().where(
            OAuthToken.client == request.client,
            OAuthToken.user == request.user
        ).execute()

        expires_in = token.pop('expires_in')
        expires = datetime.utcnow() + timedelta(seconds=expires_in)

        token_db = OAuthToken.create(
            access_token=token['access_token'],
            refresh_token=token['refresh_token'],
            token_type=token['token_type'],
            _scopes=token['scope'],
            expires=expires,
            client=request.client,
            user=request.user
        )

    # Inject extra fields to the token sent to the Client.
    token['client_id'] = request.client.client_id
    token['user_id'] = request.user.id

    return token_db

