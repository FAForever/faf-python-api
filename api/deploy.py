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


@app.route('/deployment/<repo>/<int:id>', methods=['GET'])
def deployment(repo, id):
    return app.github.deployment(owner='FAForever', repo=repo, id=id).json()


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

        if repo_name in app.config['REPO_PATHS']:
            head_commit = body['head_commit']
            branch = body['ref'].replace('refs/heads/', '')

            # check that commit is pushed for the first time
            if not head_commit['distinct']:
                return dict(status="OK"), 200

            match = re.search('Deploy: ([\w\W]+)', head_commit['message'])
            environment = match.group(1) if match else app.config['ENVIRONMENT']

            # if deploy was ordered in commit message
            # or if repository+branch is configured for auto-deployment
            if match or (repo_name in app.config['AUTO_DEPLOY']
                         and branch in app.config['AUTO_DEPLOY'][repo_name]):
                response = app.github.create_deployment(owner='FAForever',
                                                        repo=repo_name,
                                                        ref=body['ref'],
                                                        environment=environment,
                                                        description=head_commit['message'])

                if not response.status_code == 201:
                    raise Exception(response.content)


    elif event == 'deployment':
        deployment = body['deployment']
        repo = body['repository']
        if deployment['environment'] == app.config['ENVIRONMENT']:
            status, description = deploy(body['repository']['name'],
                                         body['repository']['clone_url'],
                                         deployment['ref'],
                                         deployment['sha'])
            status_response = app.github.create_deployment_status(
                owner='FAForever',
                repo=repo['name'],
                id=deployment['id'],
                state=status,
                description=description)
            app.slack.send_message(username='deploybot',
                                   text="Deployed {}:{} to {}".format(
                                       repo['name'],
                                       "{}@{}".format(deployment['ref'], deployment['sha']),
                                       deployment['environment']))
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


def deploy_game(repo_path: Path, remote_url: Path, ref: str, sha: str):
    checkout_repo(repo_path, remote_url, ref, sha)
    mod_info = parse_mod_info(Path(repo_path, 'mod_info.lua'))
    faf_modname = mod_info['_faf_modname']
    files = build_mod(repo_path)
    logger.info("Build result: {}".format(files))
    deploy_path = Path(app.config['GAME_DEPLOY_PATH'], 'updates_{}_files'.format(mod_info['_faf_modname']))
    logger.info("Deploying {} to {}".format(faf_modname, deploy_path))
    for f in files:
        destination = deploy_path / (
            f['filename'] + "." + faf_modname + "." + str(mod_info['version']) + f['sha1'][:6] + ".zip")
        logger.info("Deploying {} to {}".format(f, destination))
        shutil.copy2(str(f['path']), str(destination))
        db.execute_sql('delete from updates_{}_files where fileId = %s and version = %s;'.format(faf_modname),
                       (f['id'], mod_info['version']))
        db.execute_sql('insert into updates_{}_files '
                       '(fileId, version, md5, name) '
                       'values (%s,%s,%s,%s)'.format(faf_modname),
                       (f['id'], mod_info['version'], f['md5'], destination.name))
    return 'success', 'Deployed'


def deploy(repository, remote_url, ref, sha):
    """
    Perform deployment on this machine
    :param repository: the repository to deploy
    :param ref: ref to fetch
    :param sha: hash to verify deployment with
    :return: (status: str, description: str)
    """
    try:
        return {
            'api': deploy_web,
            'patchnotes': deploy_web,
            'fa': deploy_game
        }[repository](Path(app.config['REPO_PATHS'][repository]), remote_url, ref, sha)
    except Exception as e:
        logger.exception(e)
        return 'error', "{}: {}".format(type(e), e)
