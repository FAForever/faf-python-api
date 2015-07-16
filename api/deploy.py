"""
Holds routes for deployment based off of Github events
"""
import json
import re

from flask import request, render_template, url_for

from api import *
from api import deployers
from api.oauth import *

import hmac
from pathlib import Path



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
        if repo_name in app.config['REPO_PATHS'].keys():
            head_commit = body['head_commit']
            if not head_commit['distinct']:
                return dict(status="OK"), 200
            match = re.search('Deploy: ([\w\W]+)', head_commit['message'])
            environment = match.group(1) if match else app.config['ENVIRONMENT']
            if match or repo_name in app.config['AUTO_DEPLOY']:
                resp = app.github.create_deployment(owner='FAForever',
                                                    repo=repo_name,
                                                    ref=body['ref'],
                                                    environment=environment,
                                                    description=head_commit['message'])
                if not resp.status_code == 201:
                    raise Exception(resp.content)
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
            'api': deployers.deploy_web,
            'patchnotes': deployers.deploy_web,
        }[repository](Path(app.config['REPO_PATHS'][repository]), remote_url, ref, sha)
    except Exception as e:
        return 'error', str(e)
