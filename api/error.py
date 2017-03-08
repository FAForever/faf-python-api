from enum import Enum
from functools import wraps

from flask import request


class ErrorCode(Enum):
    AVATAR_NOT_FOUND = dict(
        code=404,
        title='Not found',
        detail='Avatar not found')
    AVATAR_ID_MISSING = dict(
        code=400,
        title='Not found',
        detail='Required parameter id is missing')
    AVATAR_FILE_EXISTS = dict(
        code=400,
        title='File exists',
        detail='Avatar file already exists')
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
    PARAMETER_MISSING = dict(
        code=103,
        title='Missing parameter',
        detail='A parameter "{0}" has to be provided.')
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
    INVALID_EMAIL = dict(
        code=130,
        title='Invalid account data',
        detail='The entered email-adress is invalid: {0}')
    INVALID_USERNAME = dict(
        code=131,
        title='Invalid account data',
        detail='The entered username is invalid: {0}')
    USERNAME_TAKEN = dict(
        code=132,
        title='Invalid account data',
        detail='The entered username is already in use: {0}')
    EMAIL_REGISTERED = dict(
        code=133,
        title='Invalid account data',
        detail='The entered email address `{0}` already has an associated account.')
    BLACKLISTED_EMAIL = dict(
        code=134,
        title='Invalid account data',
        detail='The domain of your email is blacklisted: {0}')
    TOKEN_INVALID = dict(
        code=135,
        title='Invalid operation',
        detail='The delivered token is invalid.')
    TOKEN_EXPIRED = dict(
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
    USERNAME_CHANGE_TOO_EARLY = dict(
        code=139,
        title='Username change not allowed',
        detail='Only one name change per 30 days is allowed. {0} more days to go.')
    EMAIL_CHANGE_FAILED = dict(
        code=140,
        title='Email change failed',
        detail='An unknown error happened while updating the database.'
    )
    STEAM_ID_UNCHANGEABLE = dict(
        code=141,
        title='Linking to Steam failed',
        detail='Your account is already bound to another Steam ID.'
    )
    UNKNOWN_FEATURED_MOD = dict(
        code=142,
        title='Unknown featured mod',
        detail='There is no featured mod with ID \"{}\".'
    )
    DEPLOYMENT_ERROR = dict(
        code=143,
        title='Deployment caused an error',
        detail='Error message: {}'
    )
    AUTHENTICATION_NEEDED = dict(
        code=401,
        title='Unauthorized',
        detail='You are not logged in'
    )
    FORBIDDEN = dict(
        code=403,
        title='Unauthorized',
        detail='You are not authorized to perform this action'
    )


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


# ======== Usefull decorators =======

def req_post_param(*param_names):
    def wrapper(function):
        @wraps(function)
        def decorated_function(*args, **kwargs):
            for param_name in param_names:
                if param_name not in request.form:
                    raise ApiException([Error(ErrorCode.PARAMETER_MISSING, param_name)])
            return function(*args, **kwargs)

        return decorated_function

    return wrapper
