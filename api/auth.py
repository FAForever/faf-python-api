"""
Holds the authorization url routes
"""
from flask import request, redirect, render_template

from api import *
from api.oauth import *

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
