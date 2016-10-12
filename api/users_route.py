from config import CRYPTO_KEY
import re
import time
import marisa_trie
import faf.db as db
from api import app
from flask import request
from api.error import ApiException, Error, ErrorCode
import base64
from cryptography.fernet import Fernet

@app.route('/users/create_account', methods=['POST'])
def create_account():
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
    :query email: user's email address
    :query pw_hash: user's desired client-hashed password

    """

    name = request.form.get('name')
    email = request.form.get('email')
    pw_hash = request.form.get('pw_hash')

    validate_registration_input(name, email)  # raises exception if not valid

    expiry = str(time.time() + 3600 * 24 * 14)
    plaintext = name+","+email+","+pw_hash+","+expiry
    request_hmac = Fernet(CRYPTO_KEY).encrypt(plaintext.encode())
    token = base64.urlsafe_b64encode(request_hmac)

    #send email with link to activation url
    print(token.decode("utf-8"))

    return "ok"


@app.route('/users/validate_account/<token>', methods=['GET'])
def validate_account(token=None):
    # Fuck you urlsafe_b64encode & padding and fuck you overzealous http implementations
    token = token.replace('%3d','=')
    token = token.replace('%3D','=')
    print(token)

    ciphertext = base64.urlsafe_b64decode(token.encode())
    plaintext = Fernet(CRYPTO_KEY).decrypt(ciphertext).decode("utf-8")

    name, email, pw_hash, expiry = plaintext.split(',')
    validate_registration_input(name, email)  # raises exception if not valid

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

        cursor.execute("INSERT INTO `global_rating` (`id`, `mean`, `deviation`, `numGames`, `is_active`) VALUES (%(user_id)s, %(mean)s, %(deviation)s, 0, 1)",
                       {
                           'user_id': user_id,
                           'mean': mean,
                           'deviation': deviation
                       })

        cursor.execute("INSERT INTO `ladder1v1_rating` (`id`, `mean`, `deviation`, `numGames`, `winGames`, `is_active`) VALUES (%(user_id)s, %(mean)s, %(deviation)s, 0, 0, 1)",
                       {
                           'user_id': user_id,
                           'mean': mean,
                           'deviation': deviation
                       })

    return "ok"


def validate_registration_input(login: str, user_email: str)-> bool:
    username_pattern = re.compile(r"^[^,]{1,20}$")
    email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$")


    if not email_pattern.match(user_email):
        raise ApiException([Error(ErrorCode.REGISTRATION_INVALID_EMAIL, user_email)])

    if not username_pattern.match(login):
        raise ApiException([Error(ErrorCode.REGISTRATION_INVALID_USERNAME, login)])

    with db.connection:
        cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)

        #ensure that username is unique
        cursor.execute("SELECT id FROM `login` WHERE LOWER(`login`) = %s",
                                  (login.lower(),))

        if cursor.fetchone() is not None:
            raise ApiException([Error(ErrorCode.REGISTRATION_USERNAME_TAKEN, login)])

        #ensue that email adress is unique
        cursor.execute("SELECT id FROM `login` WHERE LOWER(`email`) = %s",
                                  (user_email.lower(),))

        if cursor.fetchone() is not None:
            raise ApiException([Error(ErrorCode.REGISTRATION_EMAIL_REGISTERED, user_email)])


        # checkBlacklisted email domains (we don't like disposable email)
        cursor.execute("SELECT domain FROM email_domain_blacklist")
        rows = cursor.fetchall()
        # Get list of reversed blacklisted domains (so we can (pre)suffix-match incoming emails
        # in sublinear time)
        blacklisted_email_domains = marisa_trie.Trie(map(lambda x: x[0][::-1], rows))

        if len(blacklisted_email_domains.keys(user_email[::-1])) != 0:
            raise ApiException([Error(ErrorCode.REGISTRATION_BLACKLISTED_EMAIL, user_email)])

    return True