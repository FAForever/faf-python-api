import base64
import email
import json
import marisa_trie
import re
from email.mime.text import MIMEText

import faf.db as db
import requests
from cryptography.fernet import Fernet

import config
from api.error import ApiException, Error, ErrorCode
from config import CRYPTO_KEY

USERNAME_REGEX = re.compile("[A-Za-z]{1}[A-Za-z0-9_-]{2,15}")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$")


def validate_email(email: str) -> bool:
    # check for correct email syntax
    if not EMAIL_REGEX.match(email):
        raise ApiException([Error(ErrorCode.INVALID_EMAIL, email)])

    # check for blacklisted email domains (we don't like disposable email)
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("SELECT lower(domain) FROM email_domain_blacklist")
        rows = cursor.fetchall()
        # Get list of  blacklisted domains (so we can suffix-match incoming emails
        # in sublinear time)
        blacklisted_email_domains = marisa_trie.Trie(map(lambda x: x[0], rows))

        domain = email.split("@")[1].lower()
        if domain in blacklisted_email_domains:
            raise ApiException([Error(ErrorCode.BLACKLISTED_EMAIL, email)])

        # ensue that email adress is unique
        cursor.execute("SELECT id FROM `login` WHERE LOWER(`email`) = %s",
                       (email.lower(),))

        if cursor.fetchone() is not None:
            raise ApiException([Error(ErrorCode.EMAIL_REGISTERED, email)])

    return True


def validate_username(name: str) -> bool:
    # check for correct syntax
    if not USERNAME_REGEX.match(name):
        raise ApiException([Error(ErrorCode.INVALID_USERNAME, name)])

    with db.connection:
        cursor = db.connection.cursor()

        # ensure that username is unique
        cursor.execute("SELECT id FROM `login` WHERE LOWER(`login`) = %s",
                       (name.lower(),))

        if cursor.fetchone() is not None:
            raise ApiException([Error(ErrorCode.USERNAME_TAKEN, name)])

    return True


def send_email(logger, text, to_name, to_email, subject):
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

    logger.debug("Mandrill response: %s", json.dumps(resp.text))


def create_token(*args) -> str:
    first = True

    for param in args:
        if first:
            plaintext = str(param)
            first = False
        else:
            plaintext += "," + str(param)

    request_hmac = Fernet(CRYPTO_KEY).encrypt(plaintext.encode())
    return base64.urlsafe_b64encode(request_hmac).decode("utf-8")


def decrypt_token(token: str):
    # Fuck you urlsafe_b64encode & padding and fuck you overzealous http implementations
    token = token.replace('%3d', '=')
    token = token.replace('%3D', '=')

    ciphertext = base64.urlsafe_b64decode(token.encode())
    plaintext = Fernet(CRYPTO_KEY).decrypt(ciphertext).decode("utf-8")

    return plaintext.split(',')
