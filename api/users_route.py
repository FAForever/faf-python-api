import datetime
import logging
import time

from flask import request

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
    token = create_token(name, email, pw_hash, expiry)

    # send email with link to activation url
    logger.info(
        "User {} has registrated with email address {} -- Token expires at {:%Y-%m-%d %H:%M}".format(name, email,
                                                                                                     datetime.datetime.fromtimestamp(
                                                                                                         expiry)))

    passwordLink = "http://" + config.HOST_NAME + "/users/validate_registration/" + token

    if (config.ENVIRONMENT == "testing"):
        print(passwordLink)
    else:
        text = "Dear " + name + ",\n\n\
        welcome to the Forged Alliance Forever community.\
        Please visit the following link to activate your FAF account:\n\
        -----------------------\n\
        " + passwordLink + "\n\
        -----------------------\n\n\
        Thanks,\n\
        -- The FA Forever team"

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

    :token contains the required data (username, email, password hash, expiration date

    """

    name, email, pw_hash, expiry = decrypt_token(token)
    validate_username(name)
    validate_email(email)

    if (float(expiry) < time.time()):
        logger.error("Registration of user {} with email address {} failed (token expired)".format(name, email))
        raise ApiException([Error(ErrorCode.USER_TOKEN_EXPIRED)])

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

        # ensure that username is unique
        cursor.execute("SELECT id FROM `login` WHERE LOWER(`login`) = %s AND LOWER(`email`) = %s",
                       (name.lower(), email))

        if cursor.fetchone() is None:
            raise ApiException([Error(ErrorCode.PASSWORD_RESET_INVALID)])

    expiry = time.time() + 3600 * 24 * 14
    token = create_token(name, email, pw_hash, str(expiry))

    # send email with link to activation url
    logger.info(
        "User {} has requested change of password -- Token expires at {:%Y-%m-%d %H:%M}".format(name,
                                                                                                datetime.datetime.fromtimestamp(
                                                                                                    expiry)))

    passwordLink = "http://" + config.HOST_NAME + "/users/validate_password/" + token

    if (config.ENVIRONMENT == "testing"):
        print(passwordLink)
    else:
        text = "Dear " + name + ",\n\n\
        a new password was requested for your user.\n\
        If you did not request a new password, please delete this email.\n\n\
        Otherwise please click on the following link to reset your password:\n\
        -----------------------\n\
        " + passwordLink + "\n\
        -----------------------\n\n\
        Thanks,\n\
        -- The FA Forever team"

        send_email(logger, text, name, email, 'Forged Alliance Forever - Password reset')

    return "ok"


@app.route('/users/validate_password/<token>', methods=['GET'])
def validate_password(token=None):
    """
    Sets a new password based on a token from /users/reset_password

    **Example Request**:

    .. sourcecode:: http

       POST /users/validate_password/Z0FBQUFBQllHbVdoNFdHblhjUE01Z2l2RTQ0Z2xneXpRZ19fYUgxcmY2endsaEJ4TzdjS1EwM1QxNG8yblVwNlFhMFVuLUdKR0JETW9PZWdDdm1hLThNYUhwZnVaa0s1OGhVVF9ER09YMzFPS2RnM0dLV0hoZkUzMU9ONm1DTnFkWEgwU1VvZzZBWGs=

    **Example Response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: text/javascript

        "ok"

    :token contains the required data (username, email, password hash, expiration date

    """

    name, email, pw_hash, expiry = decrypt_token(token)

    if (float(expiry) < time.time()):
        logger.error("Registration of user {} with email address {} failed (token expired)".format(name, email))
        raise ApiException([Error(ErrorCode.USER_TOKEN_EXPIRED)])

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
            "UPDATE `login` SET `login` = %(name)s WHERE id = %(id)s",
            {
                'name': desired_name.lower(),
                'id': request.oauth.user.id
            })

    return "ok"
