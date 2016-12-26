import re

from flask import Request, Response

from api.deployment.deployment_configurations import *
from api.deployment.github import validate_github_request

logger = logging.getLogger(__name__)


class DeploymentManager(object):
    def __init__(self):
        self._configurations = []  # list[DeploymentConfiguration]

    def add(self, deployment_conf: DeploymentConfiguration) -> None:
        self._configurations.append(deployment_conf)

    def handle_request(self, request: Request) -> Response:
        logger.debug('Handling incoming github request')

        body = request.get_json()

        if len(app.config['GITHUB_SECRET']) > 0 \
                and not validate_github_request(app.config['GITHUB_SECRET'],
                                                request.data, request.headers[
                                                    'X-Hub-Signature'].split("sha1=")[
                                                    1]):
            logger.warn('Github verification failed')
            return dict(status='Github verification failed'), 400

        event = request.headers['X-Github-Event']

        repo_url = body['repository']['clone_url']
        repo_name = body['repository']['name']

        # check the push for relevance and invoke a github deployment
        if event == 'push':
            logger.debug('Github request is `push`')

            branch = body['ref'].replace('refs/heads/', '')
            head_commit = body['head_commit']

            # ignore commits that were pushed before
            if not head_commit['distinct']:
                logger.debug("Github request ignored (commit already known)")
                return dict(status='Github request ignored (commit already known)'), 200

            manual_deploy = re.search('Deploy: ([\w\W]+)', head_commit['message'])
            environment = manual_deploy.group(1) if manual_deploy else app.config['ENVIRONMENT']

            # find a list of valid configurations
            configurations = list(filter(lambda conf: conf.matches(repo_url, repo_name, branch, manual_deploy),
                                         self._configurations))  # type: list[DeploymentConfiguration]

            if len(configurations) == 0:
                logger.debug("Github request ignored (no matching configuration)")
                return dict(status='Github request ignored (no matching configuration)'), 200
            elif len(configurations) == 1:
                response = app.github.create_deployment(owner=app.config['GIT_OWNER'],
                                                        repo=repo_name,
                                                        ref=body['ref'],
                                                        environment=environment,
                                                        description=head_commit['message'])
                if response.status_code == 201:
                    logger.info('Github-deployment invoked (repo=%s, branch=%s)', repo_name, branch)
                    return dict(status='deployment invoked'), 201
                else:
                    logger.error('Github-deployment failed (repo=%s, branch=%s)', repo_name, branch)
                    raise ApiException([Error(ErrorCode.DEPLOYMENT_ERROR, response.content)])
            else:
                logger.error("Invalid deployment configuration for (repo=%s, branch=%s) ", repo_name, branch)
                raise ApiException([Error(ErrorCode.DEPLOYMENT_ERROR, "Invalid deployment configuration")])

        # check for relevance and deploy
        elif event == 'deployment':
            logger.debug('Github request is `deployment`')
            deploy_info = body['deployment']
            branch = deploy_info['ref'].replace('refs/heads/', '')

            configurations = list(filter(lambda conf: conf.matches(repo_url, repo_name, branch, True),
                                         self._configurations))  # type: list[DeploymentConfiguration]

            if len(configurations) == 0:
                logger.debug("Github request ignored (no matching configuration)")
                return dict(status='Github request ignored (no matching configuration)'), 200
            elif len(configurations) == 1:
                if deploy_info['environment'] == app.config['ENVIRONMENT']:
                    configurations[0].deploy(deploy_info['id'], deploy_info['sha'], self.on_deployment_finished)
                    return dict(status='deployment started'), 201
                else:
                    logger.debug('Skip deployment due to wrong environment')
            else:
                logger.error("Invalid deployment configuration for (repo=%s, branch=%s)", repo_name, branch)
                raise ApiException([Error(ErrorCode.DEPLOYMENT_ERROR, "Invalid deployment configuration")])

        else:
            logger.debug('Github request ignored (event `%s` irrelevant)', event)
            return dict(status='Github request ignored (event `%s` irrelevant)' % event), 200

    def on_deployment_finished(self, deploy_id: str, message: str, configuration: DeploymentConfiguration) -> None:
        logger.debug("performing post-deployment activities")

        deploy_message = "[%s] %s" % (app.config['ENVIRONMENT'], message)

        app.slack.send_message(username='deploybot', text=deploy_message)

        app.github.create_deployment_status(
            owner=app.config['GIT_OWNER'],
            repo=configuration.repo.name,
            id=deploy_id,
            state='success',
            description=deploy_message)
