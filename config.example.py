"""
Configuration file for the FAForever Python Web Api
"""
import os
from pathlib import Path

from api.deployment.deployment_configurations import WebDeploymentConfiguration, GameDeploymentConfiguration
from api.deployment.deployment_manager import DeploymentManager
from api.deployment.git import GitRepository

DATABASE = dict(
    db=os.getenv("FAF_DB_NAME", "faf_test"),
    user=os.getenv("FAF_DB_LOGIN", "root"),
    password=os.getenv("FAF_DB_PASSWORD", "banana"),
    host=os.getenv("DB_PORT_3306_TCP_ADDR", "127.0.0.1"),
    port=int(os.getenv("DB_PORT_3306_TCP_PORT", "3306")))

HOST_NAME = os.getenv("VIRTUAL_HOST", 'dev.faforever.com')

ENVIRONMENT = os.getenv("FAF_API_ENVIRONMENT", 'testing')

GAME_DEPLOY_PATH = '/content/faf/updaterNew'
BASE_GAME_EXE = '/content/faf/updaterNew/updates_faf_files/ForgedAlliance.exe'
MOD_UPLOAD_PATH = '/content/faf/vault/mods'
MOD_THUMBNAIL_PATH = '/content/faf/vault/mods_thumbs'
MAP_UPLOAD_PATH = '/content/faf/vault/maps'
MAP_PREVIEW_PATH = '/content/faf/vault/map_previews'
CONTENT_URL = 'http://content.faforever.com'

STATSD_SERVER = os.getenv('STATSD_SERVER', None)

GITHUB_USER = os.getenv("GITHUB_USER", 'some-user')
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", 'some-token')
GITHUB_SECRET = os.getenv("GITHUB_SECRET", '')
GIT_OWNER = 'FAForever'  # change this to your github account for testing purposes

API_REPO = GitRepository('https://github.com/%s/api.git' % GIT_OWNER, 'api', Path('.'))
PATCHNOTES_REPO = GitRepository('https://github.com/%s/patchnotes.git' % GIT_OWNER, 'patchnotes',
                                Path('/content/faf/patchnotes'))
GAME_REPO = GitRepository('https://github.com/%s/fa.git' % GIT_OWNER, 'fa', Path('/content/faf/repos/fa'))

DEPLOYMENTS = DeploymentManager()  # type: DeploymentManager
DEPLOYMENTS.add(WebDeploymentConfiguration(repo=API_REPO, branch='master', autodeploy=False))
DEPLOYMENTS.add(WebDeploymentConfiguration(repo=PATCHNOTES_REPO, branch='master', autodeploy=False))
DEPLOYMENTS.add(GameDeploymentConfiguration(repo=GAME_REPO, branch='master', autodeploy=False, featured_mod='faf',
                                            allow_override=False, file_extension='.nx2'))
DEPLOYMENTS.add(
    GameDeploymentConfiguration(repo=GAME_REPO, branch='deploy/fafbeta', autodeploy=True, featured_mod='fafbeta',
                                allow_override=True, file_extension='.nx4'))
DEPLOYMENTS.add(
    GameDeploymentConfiguration(repo=GAME_REPO, branch='deploy/fafdevelop', autodeploy=True, featured_mod='fafdevelop',
                                allow_override=True, file_extension='.nx5'))


FLASK_LOGIN_SECRET_KEY = os.getenv("FLASK_LOGIN_SECRET_KEY", '1234')
CRYPTO_KEY = os.getenv("CRYPTO_KEY", 'vx7rzvK2C5XxW58XRVc5vTQnQLq35UYOEP8-PYSShBs=')
SECRET_KEY = os.getenv("SECRET_KEY", '1234')
JWT_AUTH_URL_RULE = None
JWT_AUTH_HEADER_PREFIX = "Bearer"
SLACK_HOOK_URL = 'http://example.com'

MANDRILL_API_KEY = os.getenv("MANDRILL_API_KEY", '')
MANDRILL_API_URL = os.getenv("MANDRILL_API_URL", 'https://mandrillapp.com/api/1.0')

STEAM_LOGIN_URL = os.getenv("STEAM_LOGIN_URL", 'https://steamcommunity.com/openid/login')

ACCOUNT_ACTIVATION_REDIRECT = 'http://www.faforever.com/account_activated'
PASSWORD_RESET_REDIRECT = 'http://www.faforever.com/password_resetted'
