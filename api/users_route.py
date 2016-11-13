import datetime
import logging
import urllib

from flask import request, redirect

from api import app, oauth
from api.error import req_post_param
from api.helpers import *

logger = logging.getLogger(__name__)


@app.route('/users/register', methods=['POST'])
@req_post_param('name', 'email', 'pw_hash')
def create_account():
    """
    Creates a request for a new account

    **Example Request**:

    .. sourcecode:: http

       POST /users/register/

    **Example Response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: text/javascript

        "ok"

    :query name: The requested username
    :query email: user's email address
    :query pw_hash: user's desired client-hashed password

    """

    name = request.form.get('name')
    email = request.form.get('email')
    pw_hash = request.form.get('pw_hash')

    validate_username(name)
    validate_email(email)

    expiry = time.time() + 3600 * 24 * 14
    token = create_token('register', expiry, name, email, pw_hash)

    # send email with link to activation url
    logger.info(
        "User {} has registrated with email address {} -- Token expires at {:%Y-%m-%d %H:%M}".format(name, email,
                                                                                                     datetime.datetime.fromtimestamp(
                                                                                                         expiry)))

    passwordLink = "http://" + config.HOST_NAME + "/users/validate_registration/" + token

    text = "Dear " + name + ",\n\n\
    welcome to the Forged Alliance Forever community.\
    Please visit the following link to activate your FAF account:\n\
    -----------------------\n\
    " + passwordLink + "\n\
    -----------------------\n\n\
    Thanks,\n\
    -- The FA Forever team"

    if (config.ENVIRONMENT == "testing"):
        print(passwordLink)
    else:
        send_email(logger, text, name, email, 'Forged Alliance Forever - Account validation')

    return "ok"


@app.route('/users/validate_registration/<token>', methods=['GET'])
def validate_account(token=None):
    """
    Creates a new user based on a token from /users/register

    **Example Request**:

    .. sourcecode:: http

       GET /users/validate_registration/Z0FBQUFBQllHbVNQU3Y4Ui1VN3ZMSk12bUFSbUdKRG1NNDJYdzZzN0kyelk1SGNwV0FZZkdhc1lOUU1NeUkxQ0JWODU2OWhKbW5LYVZFOVBKYVhxY3JOVWZKSDRjU2xBdXFGOFJ5WkJCdzZSdnFwd2xYLVlhQkttZFBFdUZySXBOaGtpQjFoeGF2bTg=

    **Example Response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: text/javascript

        "ok"

    :token contains the required data (username, email, password hash)

    """

    name, email, pw_hash = decrypt_token('register', token)
    validate_username(name)
    validate_email(email)

    with db.connection:
        cursor = db.connection.cursor()

        cursor.execute("INSERT INTO `login` (`login`, `password`, `email`) VALUES (%(name)s, %(password)s, %(email)s)",
                       {
                           'name': name,
                           'password': pw_hash,
                           'email': email
                       })

        user_id = cursor.lastrowid
        mean = 1500
        deviation = 500

        cursor.execute(
            "INSERT INTO `global_rating` (`id`, `mean`, `deviation`, `numGames`, `is_active`) VALUES (%(user_id)s, %(mean)s, %(deviation)s, 0, 1)",
            {
                'user_id': user_id,
                'mean': mean,
                'deviation': deviation
            })

        cursor.execute(
            "INSERT INTO `ladder1v1_rating` (`id`, `mean`, `deviation`, `numGames`, `winGames`, `is_active`) VALUES (%(user_id)s, %(mean)s, %(deviation)s, 0, 0, 1)",
            {
                'user_id': user_id,
                'mean': mean,
                'deviation': deviation
            })

    return "ok"


@app.route('/users/reset_password', methods=['POST'])
@req_post_param('name', 'email', 'pw_hash')
def reset_password():
    """
    Creates a request for a new account

    **Example Request**:

    .. sourcecode:: http

       POST /users/create_account

    **Example Response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: text/javascript

        "ok"

    :query name: The requested username
    :email = request.form.get('email')
    :query pw_hash: user's desired client-hashed password

    """

    name = request.form.get('name')
    email = request.form.get('email')
    pw_hash = request.form.get('pw_hash')

    with db.connection:
        cursor = db.connection.cursor()

        # validate username and email in the database
        cursor.execute("SELECT id FROM `login` WHERE LOWER(`login`) = %s AND LOWER(`email`) = %s",
                       (name.lower(), email))

        if cursor.fetchone() is None:
            raise ApiException([Error(ErrorCode.TOKEN_INVALID)])

    expiry = time.time() + 3600 * 24 * 14
    token = create_token('reset_password', expiry, name, email, pw_hash)

    # send email with link to activation url
    logger.info(
        "User {} has requested change of password -- Token expires at {:%Y-%m-%d %H:%M}".format(name,
                                                                                                datetime.datetime.fromtimestamp(
                                                                                                    expiry)))

    passwordLink = "http://" + config.HOST_NAME + "/users/validate_password/" + token

    text = "Dear " + name + ",\n\n\
    a new password was requested for your user.\n\
    If you did not request a new password, please delete this email.\n\n\
    Otherwise please click on the following link to reset your password:\n\
    -----------------------\n\
    " + passwordLink + "\n\
    -----------------------\n\n\
    Thanks,\n\
    -- The FA Forever team"

    if (config.ENVIRONMENT == "testing"):
        print(passwordLink)
    else:
        send_email(logger, text, name, email, 'Forged Alliance Forever - Password reset')

    return "ok"


@app.route('/users/validate_password/<token>', methods=['GET'])
def validate_password(token=None):
    """
    Sets a new password based on a token from /users/reset_password

    **Example Request**:

    .. sourcecode:: http

       GET /users/validate_password/Z0FBQUFBQllHbVdoNFdHblhjUE01Z2l2RTQ0Z2xneXpRZ19fYUgxcmY2endsaEJ4TzdjS1EwM1QxNG8yblVwNlFhMFVuLUdKR0JETW9PZWdDdm1hLThNYUhwZnVaa0s1OGhVVF9ER09YMzFPS2RnM0dLV0hoZkUzMU9ONm1DTnFkWEgwU1VvZzZBWGs=

    **Example Response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: text/javascript

        "ok"

    :token contains the required data (username, email, password hash)

    """

    name, email, pw_hash = decrypt_token('reset_password', token)

    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute(
            "UPDATE `login` SET `password` = %(password)s WHERE lower(`login`) = %(name)s AND lower(`email`) = %(email)s ",
            {
                'name': name.lower(),
                'password': pw_hash,
                'email': email.lower()
            })

        if cursor.rowcount == 0:
            raise ApiException([Error(ErrorCode.PASSWORD_RESET_FAILED)])

    return "ok"


@app.route('/users/change_password', methods=['POST'])
@oauth.require_oauth('write_account_data')
@req_post_param('name', 'pw_hash_old', 'pw_hash_new')
def change_password():
    """
    Request a password change for a user

    **Example Request**:

    .. sourcecode:: http

       POST /users/create_account

    **Example Response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: text/javascript

        "ok"

    :name affected username
    :pw_hash_old password hash of the current password
    :pw_hash_new password has of the new password

    """

    name = request.form.get('name')
    pw_hash_old = request.form.get('pw_hash_old')
    pw_hash_new = request.form.get('pw_hash_new')

    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute(
            "UPDATE `login` SET `password` = lower(%(pw_hash_new)s) WHERE lower(`login`) = %(name)s AND lower(`password`) = %(pw_hash_old)s ",
            {
                'name': name.lower(),
                'pw_hash_old': pw_hash_old.lower(),
                'pw_hash_new': pw_hash_new.lower()
            })

        if cursor.rowcount == 0:
            raise ApiException([Error(ErrorCode.PASSWORD_CHANGE_FAILED)])

    return "ok"


@app.route('/users/change_name', methods=['POST'])
@oauth.require_oauth('write_account_data')
@req_post_param('desired_name')
def change_name():
    """
    Request a name change for a user

    **Example Request**:

    .. sourcecode:: http

       POST /users/change_name

    **Example Response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: text/javascript

        "ok"

    :desired_name the new username

    """

    desired_name = request.form.get('desired_name')

    validate_username(desired_name)

    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT DATEDIFF(NOW(), change_time) as days_since_last_change FROM name_history WHERE user_id=%(id)s AND DATEDIFF(NOW(), change_time) < 30 ORDER BY change_time DESC",
            {
                'id': request.oauth.user.id
            })

        entry = cursor.fetchone()

        if entry is not None:
            raise ApiException([Error(ErrorCode.USERNAME_CHANGE_TOO_EARLY, 30 - int(entry[0]))])

        cursor.execute(
            "INSERT INTO name_history (user_id, previous_name) SELECT id, login FROM login WHERE id = %(id)s",
            {
                'id': request.oauth.user.id
            }
        )

        cursor.execute(
            "UPDATE login SET login = %(name)s WHERE id = %(id)s",
            {
                'id': request.oauth.user.id,
                'name': desired_name
            }
        )

    return "ok"


@app.route('/users/link_to_steam', methods=['GET'])
@oauth.require_oauth('write_account_data')
def link_to_steam():
    """
    API stores the steam link request in a token.
    The user gets redirected to a steam login page.
    The redirect contains a callback-url where steam redirects after login to route users/validate_steam/<token>
    """

    with db.connection:
        cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT steamid from login WHERE id = %(id)s",
            {
                'id': request.oauth.user.id
            })

        entry = cursor.fetchone()

        if entry['steamid'] is not None:
            raise ApiException([Error(ErrorCode.STEAM_ID_UNCHANGEABLE)])

    expiry = time.time() + 600
    token = create_token('link_to_steam', expiry, request.oauth.user.id)

    logger.info(
        "User {} has requested steam account linking -- Token expires at {:%Y-%m-%d %H:%M}".format(
            request.oauth.user.username,
            datetime.datetime.fromtimestamp(
                expiry)))

    openid_args = {
        'openid.ns': 'http://specs.openid.net/auth/2.0',
        'openid.mode': 'checkid_setup',
        'openid.return_to': request.host_url + 'users/validate_steam/' + token,
        'openid.realm': request.host_url,
        'openid.identity': 'http://specs.openid.net/auth/2.0/identifier_select',
        'openid.claimed_id': 'http://specs.openid.net/auth/2.0/identifier_select'
    }

    steam_url = config.STEAM_LOGIN_URL + '?' + urllib.parse.urlencode(openid_args)

    return redirect(steam_url)


@app.route('/users/validate_steam/<token>', methods=['GET'])
def validate_steam_request(token=None):
    user_id = decrypt_token('link_to_steam', token)

    # extract steam account id
    match = re.search('^http://steamcommunity.com/openid/id/([0-9]{17,25})', request.args.get('openid.identity'))

    if match is None:
        return redirect(config.STEAM_LINK_FAIL_URL)

    steamID = match.group(1)

    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute(
            "UPDATE login SET steamid = %(steam_id)s WHERE id = %(id)s",
            {
                'steam_id': steamID,
                'id': user_id
            })

        return redirect(config.STEAM_LINK_SUCCESS_URL)


@app.route('/users/change_email', methods=['POST'])
@oauth.require_oauth('write_account_data')
@req_post_param('new_email')
def change_email():
    """
    Request a name change for a user

    **Example Request**:

    .. sourcecode:: http

       POST /users/change_email

    **Example Response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: text/javascript

        "ok"

    :desired_name the new username

    """

    name = request.oauth.user.username
    new_email = request.form.get('new_email')

    validate_email(new_email)

    expiry = time.time() + 3600 * 24 * 14
    token = create_token('change_email', expiry, request.oauth.user.id, new_email)

    # send email with link to activation url
    logger.info(
        "User {} has requested change of email -- Token expires at {:%Y-%m-%d %H:%M}".format(name,
                                                                                             datetime.datetime.fromtimestamp(
                                                                                                 expiry)))

    changeLink = "http://" + config.HOST_NAME + "/users/validate_email/" + token

    with db.connection:
        cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
        cursor.execute("SELECT email FROM login WHERE id = %s", request.oauth.user.id)

        user = cursor.fetchone()

        text = "Dear " + name + ",\n\n\
        you have requested to change your email account to " + new_email + ".\n\
        To confirm this change please click on the following link:\n\
        -----------------------\n\
        " + changeLink + "\n\
        -----------------------\n\n\
        Thanks,\n\
        -- The FA Forever team"

        if (config.ENVIRONMENT == "testing"):
            print(changeLink)
        else:
            send_email(logger, text, name, user['email'], 'Forged Alliance Forever - Change of email address')

    return "ok"


@app.route('/users/validate_email/<token>', methods=['GET'])
def validate_email_request(token=None):
    """
    Sets a new password based on a token from /users/change_email

    **Example Request**:

    .. sourcecode:: http

       GET /users/validate_email/Z0FBQUFBQllHbVdoNFdHblhjUE01Z2l2RTQ0Z2xneXpRZ19fYUgxcmY2endsaEJ4TzdjS1EwM1QxNG8yblVwNlFhMFVuLUdKR0JETW9PZWdDdm1hLThNYUhwZnVaa0s1OGhVVF9ER09YMzFPS2RnM0dLV0hoZkUzMU9ONm1DTnFkWEgwU1VvZzZBWGs=

    **Example Response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: text/javascript

        "ok"

    :token contains the required data (userid, new email)

    """

    userId, email = decrypt_token('change_email', token)

    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute(
            "UPDATE `login` SET `email` = %(email)s WHERE id = %(userid)s",
            {
                'userid': userId,
                'email': email.lower()
            })

        if cursor.rowcount == 0:
            raise ApiException([Error(ErrorCode.EMAIL_CHANGE_FAILED)])

    return "ok"
