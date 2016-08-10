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
