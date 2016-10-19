import sys
import subprocess
from pathlib import Path

if sys.platform == 'win32':
    GIT_PATH = 'git'
else:
    GIT_PATH = '/usr/bin/git'


def checkout_repo(repo_path: Path, remote_url: Path, ref: str, sha: str):
    if not repo_path.exists():
        raise Exception("Repository to deploy doesn't exist")
    git_command = [GIT_PATH, '-C', str(repo_path)]
    fetch_exit_code = subprocess.call(git_command + ['fetch', remote_url, ref])
    if fetch_exit_code != 0:
        raise Exception("git fetch returned nonzero code: {}".format(fetch_exit_code))
    subprocess.call(git_command + ['checkout', '-f', 'FETCH_HEAD'])
    checked_out = subprocess.check_output(git_command + ['rev-parse', 'HEAD'],
                                          universal_newlines=True).strip()
    if sha:
        if not checked_out == sha:
            raise Exception("checked out hash {} doesn't match {}".format(checked_out, sha))
