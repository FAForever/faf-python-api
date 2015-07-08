"""
Configuration file for the FAForever Python Web Api
"""
import os

DATABASE = dict(
    db=os.getenv("FAF_DB_NAME", "faf_test"),
    user=os.getenv("FAF_DB_LOGIN", "root"),
    password=os.getenv("DB_ENV_MYSQL_ROOT_PASSWORD", ""),
    host=os.getenv("DB_PORT_3306_TCP_ADDR", "127.0.0.1"),
    port=int(os.getenv("DB_PORT_3306_TCP_PORT", "3306")))

HOST_NAME = os.getenv("FAF_API_HOSTNAME", 'dev.faforever.com')

ENVIRONMENT = os.getenv("FAF_API_ENVIRONMENT", 'testing')

REPO_PATHS = {
    "api": '.',
    "patchnotes": '/opt/dev/www/patchnotes'
}

GAME_DEPLOY_PATH = '/opt/dev/www/content/faf/updaterNew'
# FIXME set paths
MOD_UPLOAD_PATH = '/opt/dev/www/content/faf/FIXME'
MAP_UPLOAD_PATH = '/opt/dev/www/content/faf/FIXME'

STATSD_SERVER = os.getenv('STATSD_SERVER', None)

GITHUB_USER = 'some-user'
GITHUB_TOKEN = 'some-token'

AUTO_DEPLOY = ['patchnotes']

FLASK_LOGIN_SECRET_KEY = os.getenv("FLASK_LOGIN_SECRET_KEY", '1234')
SLACK_HOOK_URL = 'http://example.com'
