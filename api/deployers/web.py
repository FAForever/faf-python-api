from pathlib import Path

from .git import checkout_repo

def deploy(repo_path: Path, remote_url: Path, ref: str, sha: str):
    """
    Perform deployment of a web project on this machine

    :param repo_path: full local path to the repository to deploy
    :param remote_url: url of git remote to fetch from
    :param ref: ref to fetch
    :param sha: hash to verify deployment with
    :return: (status: str, description: str)
    """
    checkout_repo(repo_path, remote_url, ref, sha)
    restart_file = Path(repo_path, 'tmp/restart.txt')
    restart_file.touch()
