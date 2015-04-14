"""
Holds the authorization url routes
"""
from flask import request, redirect, render_template

from api import *
from api.oauth import *

from time import mktime

@app.route('/oauth/check/<access_token>', methods=['GET', 'POST'])
def oauth_check_token(access_token):
    try:
        token = OAuthToken.get(OAuthToken.access_token == access_token)

        active = token.expires < datetime.now()

        res = dict(
            active = active,
            exp = mktime(token.expires.timetuple())
        )

        res['scope'] = token._scopes

        res['client_id'] = token.client.client_id
        res['user_id'] = token.user.id

        return res
    except DoesNotExist:
        return dict(active = False)

@app.route('/oauth/token')
@oauth.token_handler
def access_token():
    return None


@app.route('/oauth/authorize', methods=['GET', 'POST'])
@oauth.authorize_handler
def authorize(*args, **kwargs):
    user = current_user()
    if not user:
        return redirect('/')

    if request.method == 'GET':
        client_id = kwargs.get('client_id')
        client = OAuthClient.get(OAuthClient.client_id == client_id)
        kwargs['client'] = client
        kwargs['user'] = user
        return render_template('authorize.html', **kwargs)

    confirm = request.form.get('confirm', 'no')
    return confirm == 'yes'
