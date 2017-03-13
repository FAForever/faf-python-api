from unittest.mock import patch, Mock

import pytest

from api.helpers import *


@pytest.fixture
def setup_users(request, app):
    app.debug = True
    with db.connection:
        cursor = db.connection.cursor()
        cursor.execute("TRUNCATE TABLE game_player_stats")
        cursor.execute("TRUNCATE TABLE game_stats")
        cursor.execute("TRUNCATE TABLE ladder1v1_rating")
        cursor.execute("TRUNCATE TABLE global_rating")
        cursor.execute("delete from login")
        cursor.execute("""INSERT INTO login
        (id, login, password, email) VALUES
        (1, 'abc', 'pw_a', 'a@aa.aa'),
        (2, 'bcd', 'pw_b', 'b@bb.bb')""")
        cursor.execute("TRUNCATE TABLE email_domain_blacklist")
        cursor.execute("INSERT INTO email_domain_blacklist VALUES ('zzz.com'), ('abc.de')")


def test_validate_email_success(setup_users):
    assert validate_email("valid@email.com") == True


def test_validate_email_illegal_syntax(setup_users):
    with pytest.raises(ApiException) as excInfo:
        validate_email("email.without.domain")

    assert excInfo.value.errors[0].code == ErrorCode.INVALID_EMAIL


def test_validate_email_blacklisted(setup_users):
    with pytest.raises(ApiException) as excInfo:
        validate_email("a@ZZZ.com")

    assert excInfo.value.errors[0].code == ErrorCode.BLACKLISTED_EMAIL


def test_validate_email_taken(setup_users):
    with pytest.raises(ApiException) as excInfo:
        validate_email("a@AA.aa")

    assert excInfo.value.errors[0].code == ErrorCode.EMAIL_REGISTERED


def test_validate_username_success(setup_users):
    assert validate_username("new_user") == True


def test_validate_username_illegal_syntax(setup_users):
    with pytest.raises(ApiException) as excInfo:
        validate_username("xxx yyy")

    assert excInfo.value.errors[0].code == ErrorCode.INVALID_USERNAME


def test_validate_username_taken(setup_users):
    with pytest.raises(ApiException) as excInfo:
        validate_username("Bcd")

    assert excInfo.value.errors[0].code == ErrorCode.USERNAME_TAKEN


def test_token_simulate_registration():
    expires_at = time.time() + 60
    name = "new_user"
    email = "new_user@faforever.com"
    pw_hash = "123456789!"

    result = decrypt_token('register', create_token('register', expires_at, name, email, pw_hash))

    assert result[0] == name
    assert result[1] == email
    assert result[2] == pw_hash


def test_token_expired():
    expires_at = time.time() - 60
    name = "new_user"
    email = "new_user@faforever.com"
    pw_hash = "123456789!"

    with pytest.raises(ApiException) as excInfo:
        result = decrypt_token('register', create_token('register', expires_at, name, email, pw_hash))

    assert excInfo.value.errors[0].code == ErrorCode.TOKEN_EXPIRED


@patch('requests.post')
def test_send_email(post_function):
    response = Mock()
    response.text = "{}"
    post_function.return_value = response

    send_email(Mock(), "someText", "someName", "someEmail", "someSubject")

    assert post_function.call_count == 1
