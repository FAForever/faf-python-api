from enum import Enum


class ErrorCode(Enum):
    ACHIEVEMENT_CANT_INCREMENT_STANDARD = dict(
        code=100,
        title='Invalid operation',
        detail='Only incremental achievements can be incremented. Achievement ID: {0}.')
    ACHIEVEMENT_CANT_UNLOCK_INCREMENTAL = dict(
        code=101,
        title='Invalid operation',
        detail='Only standard achievements can be unlocked directly. Achievement ID: {0}.')
    UPLOAD_FILE_MISSING = dict(
        code=102,
        title='Missing file',
        detail='A file has to be provided as parameter "file".')
    UPLOAD_METADATA_MISSING = dict(
        code=103,
        title='Missing metadata',
        detail='A parameter "metadata" has to be provided.')
    UPLOAD_INVALID_FILE_EXTENSION = dict(
        code=104,
        title='Invalid file extension',
        detail='File must have the following extension: {0}.')
    MAP_NAME_TOO_LONG = dict(
        code=105,
        title='Invalid map name',
        detail='The map name must not exceed {0} characters, was: {1}')
    MAP_NOT_ORIGINAL_AUTHOR = dict(
        code=106,
        title='Permission denied',
        detail='Only the original author is allowed to upload new versions of map: {0}.')
    MAP_VERSION_EXISTS = dict(
        code=107,
        title='Duplicate map version',
        detail='Map "{0}" with version "{1}" already exists.')
    MAP_NAME_CONFLICT = dict(
        code=108,
        title='Name clash',
        detail='Another map with file name "{0}" already exists.')
    MAP_NAME_MISSING = dict(
        code=109,
        title='Missing map name',
        detail='The scenario file must specify a map name.')
    MAP_DESCRIPTION_MISSING = dict(
        code=110,
        title='Missing description',
        detail='The scenario file must specify a map description.')
    MAP_FIRST_TEAM_FFA = dict(
        code=111,
        title='Invalid team name',
        detail='The name of the first team has to be "FFA".')
    MAP_TYPE_MISSING = dict(
        code=112,
        title='Missing map type',
        detail='The scenario file must specify a map type.')
    MAP_SIZE_MISSING = dict(
        code=113,
        title='Missing map size',
        detail='The scenario file must specify a map size.')
    MAP_VERSION_MISSING = dict(
        code=114,
        title='Missing map version',
        detail='The scenario file must specify a map version.')
    QUERY_INVALID_SORT_FIELD = dict(
        code=115,
        title='Invalid sort field',
        detail='Sorting by "{0}" is not supported')
    QUERY_INVALID_PAGE_SIZE = dict(
        code=116,
        title='Invalid page size',
        detail='Page size is not valid: {0}')
    QUERY_INVALID_PAGE_NUMBER = dict(
        code=117,
        title='Invalid page number',
        detail='Page number is not valid: {0}')
    MOD_NAME_MISSING = dict(
        code=118,
        title='Missing mod name',
        detail='The file mod_info.lua must contain a property "name".')
    MOD_UID_MISSING = dict(
        code=119,
        title='Missing mod UID',
        detail='The file mod_info.lua must contain a property "uid".')
    MOD_VERSION_MISSING = dict(
        code=120,
        title='Missing mod version',
        detail='The file mod_info.lua must contain a property "version".')
    MOD_DESCRIPTION_MISSING = dict(
        code=121,
        title='Missing mod description',
        detail='The file mod_info.lua must contain a property "description".')
    MOD_UI_ONLY_MISSING = dict(
        code=122,
        title='Missing mod type',
        detail='The file mod_info.lua must contain a property "ui_only".')
    MOD_NAME_TOO_LONG = dict(
        code=123,
        title='Invalid mod name',
        detail='The mod name must not exceed {0} characters, was: {1}')
    MOD_NOT_ORIGINAL_AUTHOR = dict(
        code=124,
        title='Permission denied',
        detail='Only the original author is allowed to upload new versions of mod: {0}.')
    MOD_VERSION_EXISTS = dict(
        code=125,
        title='Duplicate mod version',
        detail='Mod "{0}" with version "{1}" already exists.')
    MOD_AUTHOR_MISSING = dict(
        code=126,
        title='Missing mod author',
        detail='The file mod_info.lua must contain a property "author".')
    QUERY_INVALID_RATING_TYPE = dict(
        code=127,
        title='Invalid rating type',
        detail='Rating type is not valid: {0}. Please pick "1v1" or "global".')
    LOGIN_DENIED_BANNED = dict(
        code=128,
        title='Login denied',
        detail='You are currently banned: {0}')
    MOD_NAME_CONFLICT = dict(
        code=129,
        title='Name clash',
        detail='Another mod with file name "{0}" already exists.')
    REGISTRATION_INVALID_EMAIL = dict(
        code=130,
        title='Registration failed',
        detail='The entered email-adress is invalid: {0}')
    REGISTRATION_INVALID_USERNAME = dict(
        code=131,
        title='Registration failed',
        detail='The entered username is invalid: {0}')
    REGISTRATION_USERNAME_TAKEN = dict(
        code=132,
        title='Registration failed',
        detail='The entered username is already in use: {0}')
    REGISTRATION_EMAIL_REGISTERED = dict(
        code=133,
        title='Registration failed',
        detail='The entered email address `{0}` already has an associated account. Please request a new password instead.')
    REGISTRATION_BLACKLISTED_EMAIL = dict(
        code=134,
        title='Registration failed',
        detail='The domain of your email is blacklisted: {0}')
    PASSWORD_RESET_INVALID = dict(
        code=135,
        title='Invalid operation',
        detail='The delivered token is invalid.')
    USER_TOKEN_EXPIRED = dict(
        code=136,
        title='Invalid operation',
        detail='The delivered token has expired.')
    PASSWORD_RESET_FAILED = dict(
        code=137,
        title='Password reset failed',
        detail='Username and/or email did not match.')
    PASSWORD_CHANGE_FAILED = dict(
        code=138,
        title='Password change failed',
        detail='Username and/or old password did not match.')

class Error:
    def __init__(self, code: ErrorCode, *args):
        self.code = code
        self.args = args

    def to_dict(self):
        return {
            'code': self.code.value['code'],
            'title': self.code.value['title'],
            'detail': self.code.value['detail'].format(*self.args),
            'meta': {
                'args': self.args
            }
        }


class ApiException(Exception):
    def __init__(self, errors, status_code=400):
        self.errors = errors
        self.status_code = status_code

    def to_dict(self):
        return {
            'errors': [error.to_dict() for error in self.errors]
        }
