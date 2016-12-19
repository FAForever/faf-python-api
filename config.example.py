"""
Configuration file for the FAForever Python Web Api
"""
import os

DATABASE = dict(
    db=os.getenv("FAF_DB_NAME", "faf_test"),
    user=os.getenv("FAF_DB_LOGIN", "root"),
    password=os.getenv("FAF_DB_PASSWORD", "banana"),
    host=os.getenv("DB_PORT_3306_TCP_ADDR", "127.0.0.1"),
    port=int(os.getenv("DB_PORT_3306_TCP_PORT", "3306")))

HOST_NAME = os.getenv("VIRTUAL_HOST", 'dev.faforever.com')

ENVIRONMENT = os.getenv("FAF_API_ENVIRONMENT", 'testing')

# Server path which will contain all git repositories. Primarily used for game files
REPO_CONTAINER = '/content/faf/repos'
TEMP_CONTAINER = '/content/faf/temp'
BASE_GAME_EXE = '/content/faf/updaterNew/updates_faf_files/ForgedAlliance.exe'

DEPLOY_BRANCHES = {
    # branch name : game mode
    'master': 'faf',
    'deploy/fafbeta': 'fafbeta',
    'deploy/fafdevelop': 'fafdevelop'
}

MODE_NX = {
    # game mode : .zip extension
    'faf': '.nx2',
    'fafbeta': '.nx4',
    'fafdevelop': '.nx5'
}

GAME_DEPLOY_PATH = '/content/faf/updaterNew'
MOD_UPLOAD_PATH = '/content/faf/vault/mods'
MOD_THUMBNAIL_PATH = '/content/faf/vault/mods_thumbs'
MAP_UPLOAD_PATH = '/content/faf/vault/maps'
MAP_PREVIEW_PATH = '/content/faf/vault/map_previews'
CONTENT_URL = 'http://content.faforever.com'

STATSD_SERVER = os.getenv('STATSD_SERVER', None)

GITHUB_USER = 'some-user'
GITHUB_TOKEN = 'some-token'
GIT_URL = 'https://github.com/FAForever/'

AUTO_DEPLOY = ['patchnotes']

FLASK_LOGIN_SECRET_KEY = os.getenv("FLASK_LOGIN_SECRET_KEY", '1234')
CRYPTO_KEY = 'vx7rzvK2C5XxW58XRVc5vTQnQLq35UYOEP8-PYSShBs='
SECRET_KEY = os.getenv("SECRET_KEY", '1234')
JWT_AUTH_URL_RULE = None
JWT_AUTH_HEADER_PREFIX = "Bearer"
SLACK_HOOK_URL = 'http://example.com'

MANDRILL_API_KEY = os.getenv("MANDRILL_API_KEY", '')
MANDRILL_API_URL = os.getenv("MANDRILL_API_URL", 'https://mandrillapp.com/api/1.0')

STEAM_LOGIN_URL = os.getenv("STEAM_LOGIN_URL", 'https://steamcommunity.com/openid/login')
