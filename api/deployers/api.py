import sys
import subprocess
from pathlib import Path

if sys.platform == 'win32':
    GIT_PATH = 'git'
else:
    GIT_PATH = '/usr/bin/git'

def deploy(repo_path: Path, clone_url: str, ref: str, sha: str):
    """
    Perform deployment on this machine
    :param repo_path: full local path to the repository to deploy
    :param ref: ref to fetch
    :param sha: hash to verify deployment with
    :return: (status: str, description: str)
    """
    if not repo_path.exists():
        raise Exception("Repository to deploy doesn't exist")
    git_command = [GIT_PATH, '-C', str(repo_path)]
    fetch_exit_code = subprocess.call(git_command + ['fetch', clone_url, ref])
    if fetch_exit_code != 0:
        return "error", "git fetch returned nonzero code: {}".format(fetch_exit_code)
    subprocess.call(git_command + ['checkout', '-f', 'FETCH_HEAD'])
    checked_out = subprocess.check_output(git_command + ['rev-parse', 'HEAD']).strip().decode()
    if not checked_out == sha:
        return "failure", "checked out hash {} doesn't match {}".format(checked_out, sha)
    restart_file = Path(repo_path, '/tmp/restart.txt')
    restart_file.touch()
    return "success", "Deployed successfully"
