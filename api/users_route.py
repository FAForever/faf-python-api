import base64
import datetime
import email
import json
import logging
import marisa_trie
import re
import time
from email.mime.text import MIMEText

import faf.db as db
import requests
from cryptography.fernet import Fernet
from flask import request

import config
from api import app
from api.error import ApiException, Error, ErrorCode
from config import CRYPTO_KEY

logger = logging.getLogger(__name__)

def create_token(name: str, email: str, pw_hash: str, expiry: int) -> str:
    plaintext = name + "," + email + "," + pw_hash + "," + str(expiry)
    request_hmac = Fernet(CRYPTO_KEY).encrypt(plaintext.encode())
    return base64.urlsafe_b64encode(request_hmac).decode("utf-8")


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

    expiry = time.time() + 3600 * 24 * 14
    token = create_token(name, email, pw_hash, str(expiry))

    #send email with link to activation url
    logger.info(
        "User {} has registrated with email address {} -- Token expires at {:%Y-%m-%d %H:%M}".format(name, email,
                                                                                                     datetime.datetime.fromtimestamp(
                                                                                                         expiry)))

    passwordLink = "http://" + config.HOST_NAME + "/users/validate_account/" + token

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

        send_email(text, name, email, 'Forged Alliance Forever - Account validation')

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

    if (float(expiry) < time.time()):
        logger.error("Registration of user {} with email address {} failed (token expired)".format(name, email))
        raise ApiException([Error(ErrorCode.REGISTRATION_TOKEN_EXPIRED)])

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
        cursor = db.connection.cursor()

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
        cursor.execute("SELECT lower(domain) FROM email_domain_blacklist")
        rows = cursor.fetchall()
        # Get list of  blacklisted domains (so we can suffix-match incoming emails
        # in sublinear time)
        blacklisted_email_domains = marisa_trie.Trie(map(lambda x: x[0], rows))

        domain = user_email.split("@")[1].lower()
        if domain in blacklisted_email_domains:
            raise ApiException([Error(ErrorCode.REGISTRATION_BLACKLISTED_EMAIL, user_email)])

    return True


def send_email(text, to_name, to_email, subject):
    msg = MIMEText(text)

    msg['Subject'] = subject
    msg['From'] = email.utils.formataddr(('Forged Alliance Forever', "admin@faforever.com"))
    msg['To'] = email.utils.formataddr((to_name, to_email))

    logger.debug("Sending mail to " + to_email)
    url = config.MANDRILL_API_URL + "/messages/send-raw.json"
    headers = {'content-type': 'application/json'}
    resp = requests.post(url,
                         data=json.dumps({
                             "key": config.MANDRILL_API_KEY,
                             "raw_message": msg.as_string(),
                             "from_email": 'admin@faforever.com',
                             "from_name": "Forged Alliance Forever",
                             "to": [
                                 to_email
                             ],
                             "async": False
                         }),
                         headers=headers)
    print(json.dumps(resp.text))
    logger.debug("Mandrill response: %s", json.dumps(resp.text))
