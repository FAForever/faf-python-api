"""
Holds routes for deployment based off of Github events
"""
import hmac
import logging
import re
import shutil
from pathlib import Path

from faf.tools.fa.build_mod import build_mod
from faf.tools.fa.mods import parse_mod_info

from api.oauth_handlers import *
from .git import checkout_repo

logger = logging.getLogger(__name__)

github_session = None


def validate_github_request(body, signature):
    digest = hmac.new(app.config['GITHUB_SECRET'],
                      body, 'sha1').hexdigest()
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
    :return:
    """
    body = request.get_json()
    if not validate_github_request(request.data,
                                   request.headers['X-Hub-Signature'].split("sha1=")[1]):
        return dict(status="Invalid request"), 400
    event = request.headers['X-Github-Event']
    if event == 'push':
        repo_name = body['repository']['name']
        if repo_name in app.config['REPO_PATHS'].keys():
            head_commit = body['head_commit']
            if not head_commit['distinct']:
                return dict(status="OK"), 200
            match = re.search('Deploy: ([\w\W]+)', head_commit['message'])
            environment = match.group(1) if match else app.config['ENVIRONMENT']
            if match or repo_name in app.config['AUTO_DEPLOY']:
                resp = app.github.create_deployment(owner='FAForever',
                                                    repo=repo_name,
                                                    branch=body['ref'],
                                                    environment=environment,
                                                    description=head_commit['message'])
                if not resp.status_code == 201:
                    raise Exception(resp.content)
    elif event == 'deployment':
        body_deployment = body['deployment']
        repo = body['repository']
        if body_deployment['environment'] == app.config['ENVIRONMENT']:
            status, description = deploy_route(body['repository']['name'],
                                               body['repository'],
                                               body_deployment['ref'],
                                               body_deployment['sha'])
            status_response = app.github.create_deployment_status(
                owner='FAForever',
                repo=repo['name'],
                id=body_deployment['id'],
                state=status,
                description=description)
            app.slack.send_message(username='deploybot',
                                   text="Deployed {}:{} to {}".format(
                                       repo['name'],
                                       "{}@{}".format(body_deployment['ref'], body_deployment['sha']),
                                       body_deployment['environment']))
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


def deploy_web(repo_path: Path, remote_url: Path, ref: str, sha: str):
    checkout_repo(repo_path, remote_url, ref, sha)
    restart_file = Path(repo_path, 'tmp/restart.txt')
    restart_file.touch()
    return 'success', 'Deployed'


def deploy_game(repository: str, remote_url: Path, branch: str, mode: str, sha: str):
    repo_path = Path(app.config['REPO_PATHS'][repository])
    checkout_repo(repo_path, remote_url, branch, sha)  # Checkout the intended state on the server repo

    mod_info = parse_mod_info(Path(repo_path, 'mod_info.lua'))  # Harvest data from mod_info.lua
    game_mode = mode or mod_info['_faf_modname']

    version = str(mod_info['version'])

    files = build_mod(repo_path)  # Build the mod from the fileset we just checked out
    logger.info('Build result: {}'.format(files))

    deploy_path = Path(app.config['GAME_DEPLOY_PATH'], 'updates_{}_files'.format(game_mode))
    logger.info('Deploying {} to {}'.format(game_mode, deploy_path))

    for file in files:
        # Organise the files needed into their final setup and pack as .zip
        destination = deploy_path / (file['filename'] + '.' + game_mode + '.' + version + file['sha1'][:6] + '.zip')
        logger.info('Deploying {} to {}'.format(file, destination))
        shutil.copy2(str(file['path']), str(destination))

        # Update the database with the new mod
        db.execute_sql('delete from updates_{}_files where fileId = %s and version = %s;'.format(game_mode),
                       (file['id'], version))  # Out with the old
        db.execute_sql('insert into updates_{}_files '
                       '(fileId, version, md5, name) '
                       'values (%s,%s,%s,%s)'.format(game_mode),
                       (file['id'], version, file['md5'], destination.name))  # In with the new

    return 'Success', 'Deployed ' + repository + ' branch ' + branch + ' to ' + game_mode


@app.route('/deploy/<str:repository>/<str:branch>/<str:mode>', methods=['GET'])
def deploy_route(repository, branch, mode, sha):
    """
    Perform deployment on this machine
    :param repository: the repository to deploy
    :param branch: branch to fetch
    :param mode: game mode that we're deploying to
    :param sha: hash to verify deployment with. Not used when called by API
    :return: (status: str, description: str)
    """

    github_url = app.config['GIT_URL']
    remote_url = github_url + repository + '.git'

    try:
        return {
            'api': deploy_web,
            'patchnotes': deploy_web,
            'fa': deploy_game
        }[repository](Path(app.config['REPO_PATHS'][repository]), remote_url, branch, mode, sha)
    except Exception as e:
        logger.exception(e)
        return 'error', "{}: {}".format(type(e), e)


@app.route('/listmodes', methods=['GET'])
def list_modes():
    db.execute_sql('select gamemod, name from game_featuredMods ')
