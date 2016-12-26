"""
Holds routes for deployment based off of Github events
"""
from api import app, request

@app.route('/deployment/<repo>/<int:id>', methods=['GET'])
def deployment(repo, id):
    return app.github.deployment(owner=app.config['GIT_OWNER'], repo=repo, id=id).json()


@app.route('/deployment/status/<repo>', methods=['GET'])
def deployments(repo):
    return {
        'status': 'OK',
        'deployments': app.github.deployments(owner=app.config['GIT_OWNER'], repo=repo).json()
    }


@app.route('/deployment/github', methods=['POST'])
def github_hook():
    """
    Generic github hook suitable for receiving github status events.
    :return:
    """
    return app.config['DEPLOYMENTS'].handle_request(request)
