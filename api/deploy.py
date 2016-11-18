"""
Holds routes for deployment based off of Github events
"""
import hmac
import logging
import shutil
import os
from pathlib import Path

from pymysql.cursors import DictCursor

from faf.tools.fa.build_mod import build_mod
from faf.tools.fa.mods import parse_mod_info
from faf import db

from api.oauth_handlers import *
from .git import checkout_repo

logger = logging.getLogger(__name__)

github_session = None


def validate_github_request(data, signature):
    digest = hmac.new(app.config['GITHUB_SECRET'],
                      data, 'sha1').hexdigest()
    return hmac.compare_digest(digest, signature)


@app.route('/deployment/<repo>/<int:deployment_id>', methods=['GET'])
def deployment(repo, deployment_id):
    return app.github.deployment(owner='FAForever', repo=repo, id=deployment_id).json()


@app.route('/status/<repo>', methods=['GET'])
def deployments(repo):
    return {
        'status': 'OK',
        'deployments': app.github.deployments(owner='FAForever', repo=repo).json()
    }


@app.route('/github', methods=['POST'])
def github_hook():
    """
    Generic github hook suitable for receiving github status events.
    Sent a 'request' from github consisting of a table upon an appropriate event (eg - Push)
    :return:
    """

    #  Validate that we have a a legitimate github request
    # if not validate_github_request(request.data, request.headers['X-Hub-Signature'].split("sha1=")[1]):
    #   return dict(status="Invalid request"), 400

    event = request.headers['X-Github-Event']

    if event == 'push':
        body = request.get_json()
        branch = body['ref'].replace('refs/heads/', '')
        game_mode = app.config['DEPLOY_BRANCHES'][branch]  # Check that this branch matches a game mode we want

        if not branch or not game_mode:
            return

        if game_mode:
            repo = body['repository']
            commit = body['after']

            # Build mod on database from git and write to download system
            status, description = deploy_route(repo['name'],
                                               branch,
                                               game_mode,
                                               commit)
            # Create status update on github
            status_response = app.github.create_deployment_status(owner='FAForever',
                                                                  repo=repo['name'],
                                                                  id=repo['id'],
                                                                  state=status,
                                                                  description=description)
            # Create status update on Slack
            app.slack.send_message(username='deploybot',
                                   text="Deployed {}:{} to {}".format(
                                       repo['name'],
                                       "{}@{}".format(branch, commit),
                                       game_mode))
            # Create status responses
            if status_response.status_code == 201:
                return (dict(status=status,
                             description=description),
                        201)
            else:
                return ((dict(status='error',
                              description="Failure creating github deployment status: {}"
                              .format(status_response.content))),
                        status_response.status_code)
    return dict(status="OK"), 200


def deploy_web(repo_path: Path, repo_url: Path, container_path: Path, branch: str, commit: str):
    checkout_repo(repo_path, repo_url, container_path, branch, commit)
    restart_file = Path(repo_path, 'tmp/restart.txt')
    restart_file.touch()
    return 'success', 'Deployed'


def deploy_game(repo_path: Path, repo_url: Path, container_path: Path, branch: str, game_mode: str, commit: str):
    checkout_repo(repo_path, repo_url, container_path, branch, commit)  # Checkout the intended state on the server repo

    mod_info = parse_mod_info(repo_path)  # Harvest data from mod_info.lua
    version = mod_info['version']

    files = build_mod(repo_path, mod_info)  # Build the mod from the fileset we just checked out
    logger.info('Build result: {}'.format(files))

    deploy_path = Path(app.config['GAME_DEPLOY_PATH'] + '/' + str(version))
    if not deploy_path.exists():
        os.mkdir(str(deploy_path))

    logger.info('Deploying {} to {}'.format(game_mode, deploy_path))

    with db.connection:
        for file in files:
            # Organise the files needed into their final setup and pack as .zip
            destination = deploy_path / (file['filename'] + '.' + game_mode + '.' + str(version) + file['sha1'][:6] + '.zip')
            logger.info('Deploying {} to {}'.format(file, destination))
            shutil.copy2(str(file['path']), str(destination))

            # Update the database with the new mod
            cursor = db.connection.cursor(DictCursor)
            cursor.execute("delete from updates_{}_files where fileId = %s and version = %s;".format(game_mode),
                           (file['id'], version))

            cursor.execute('insert into updates_{}_files '
                           '(fileId, version, md5, name) '
                           'values (%s,%s,%s,%s)'.format(game_mode),
                           (file['id'], version, file['md5'], destination.name))

    return 'Success', 'Deployed ' + str(repo_url) + ' branch ' + branch + ' to ' + game_mode


def deploy_route(repository: str, branch: str, game_mode: str, commit: str):
    """
    Perform deployment on this machine
    :param repository: the source repository
    :param branch: the source branch
    :param game_mode: the game mode we are deploying to
    :param commit: commit hash to verify deployment
    :return: (status: str, description: str)
    """

    github_url = app.config['GIT_URL']
    repo_url = github_url + repository + '.git'
    container_path = Path(app.config['REPO_CONTAINER'])  # Contains all the git repositories on the server

    if not container_path.exists():
        raise Exception("No git repository container path")

    repo_path = Path(str(container_path) + '/' + repository)  # The repo we want to be using this time

    try:
        return {
            'api': deploy_web,
            'patchnotes': deploy_web,
            'fa': deploy_game
        }[repository](repo_path, repo_url, container_path, branch, game_mode, commit)
    except Exception as e:
        logger.exception(e)
        return 'error', "{}: {}".format(type(e), e)
