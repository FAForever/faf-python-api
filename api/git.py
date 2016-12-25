import subprocess
import sys
from pathlib import Path

if sys.platform == 'win32':
    GIT_PATH = 'git'
else:
    GIT_PATH = '/usr/bin/git'


def checkout_repo(repo_path: Path, remote_url: str, ref: str, sha: str):
    repo_parent = repo_path.parent
    git_command = [GIT_PATH, '-C', str(repo_parent)]

    if not repo_path.exists():  # We don't have the repo, so we need to clone it
        clone_exit_code = subprocess.call(git_command + ['clone', remote_url, str(repo_path)])
        if clone_exit_code != 0:
            raise Exception('git clone returned nonzero code: {}'.format(clone_exit_code))

    git_command = [GIT_PATH, '-C', str(repo_path)]
    fetch_exit_code = subprocess.call(git_command + ['fetch', str(remote_url), ref])
    if fetch_exit_code != 0:
        raise Exception("git fetch returned nonzero code: {}".format(fetch_exit_code))
    subprocess.call(git_command + ['checkout', '-f', 'FETCH_HEAD'])
    checked_out = subprocess.check_output(git_command + ['rev-parse', 'HEAD'],
                                          universal_newlines=True).strip()
    if not checked_out == sha:
        raise Exception("checked out hash {} doesn't match {}".format(checked_out, sha))


class GitRepository(object):
    """
    A data structure to store all relevant information of a git repository
    """

    def __init__(self, url: str, name: str, path: Path):
        self.url = url  # type: str
        self.name = name  # type: str
        self.path = path  # type: Path
