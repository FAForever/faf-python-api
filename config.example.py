"""
Configuration file for the FAForever Python Web Api
"""
import os

DATABASE = dict(
    db=os.getenv("FAF_DB_NAME", "faf_test"),
    user=os.getenv("FAF_DB_USER", "root"),
    password=os.getenv("FAF_DB_PW", ""),
    host=os.getenv("FAF_DB_HOST", "127.0.0.1"))

HOST_NAME = os.getenv("FAF_API_HOSTNAME", 'dev.faforever.com')

ENVIRONMENT = os.getenv("FAF_API_ENVIRONMENT", 'testing')

REPO_PATHS = {
    "api": '.',
    "patchnotes": '/opt/dev/www/patchnotes'
}

GAME_DEPLOY_PATH = '/opt/dev/www/content/faf/updaterNew'

GITHUB_USER = 'some-user'
GITHUB_TOKEN = 'some-token'

AUTO_DEPLOY = ['patchnotes']
