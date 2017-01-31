from pathlib import Path
from unittest.mock import patch

import pytest

from api.deployment.git import GIT_PATH, GitCloneException, GitFetchException, GitCheckoutException
from api.deployment.git import checkout_repo


@patch("subprocess.call")
@patch("subprocess.check_output")
def test_checkout_repo_success(mock_check_output, mock_call):
    def git_handler(commands):
        if ' '.join(commands) == GIT_PATH + " -C . clone http://someurl.com somepath":
            return 0
        elif ' '.join(commands) == GIT_PATH + " -C somepath fetch http://someurl.com someref":
            return 0

    mock_call.side_effect = git_handler
    mock_check_output.return_value = "commitID"

    checkout_repo(Path("somepath"), "http://someurl.com", "someref", "commitID")

    assert mock_call.call_count == 3
    assert mock_check_output.call_count == 1


@patch("subprocess.call")
@patch("subprocess.check_output")
def test_checkout_repo_clone_fails(mock_check_output, mock_call):
    def git_handler(commands):
        if ' '.join(commands) == GIT_PATH + " -C . clone http://someurl.com somepath":
            return 1
        elif ' '.join(commands) == GIT_PATH + " -C somepath fetch http://someurl.com someref":
            return 0

    with pytest.raises(GitCloneException):
        mock_call.side_effect = git_handler
        mock_check_output.return_value = "commitID"

        checkout_repo(Path("somepath"), "http://someurl.com", "someref", "commitID")

        assert mock_call.call_count == 1
        assert mock_check_output.call_count == 0


@patch("subprocess.call")
@patch("subprocess.check_output")
def test_checkout_repo_fetch_fails(mock_check_output, mock_call):
    def git_handler(commands):
        if ' '.join(commands) == GIT_PATH + " -C . clone http://someurl.com somepath":
            return 0
        elif ' '.join(commands) == GIT_PATH + " -C somepath fetch http://someurl.com someref":
            return 1

    with pytest.raises(GitFetchException):
        mock_call.side_effect = git_handler
        mock_check_output.return_value = "commitID"

        checkout_repo(Path("somepath"), "http://someurl.com", "someref", "commitID")

        assert mock_call.call_count == 2
        assert mock_check_output.call_count == 0


@patch("subprocess.call")
@patch("subprocess.check_output")
def test_checkout_repo_checkout_fails(mock_check_output, mock_call):
    def git_handler(commands):
        if ' '.join(commands) == GIT_PATH + " -C . clone http://someurl.com somepath":
            return 0
        elif ' '.join(commands) == GIT_PATH + " -C somepath fetch http://someurl.com someref":
            return 0

    with pytest.raises(GitCheckoutException):
        mock_call.side_effect = git_handler
        mock_check_output.return_value = "wrongCommitID"

        checkout_repo(Path("somepath"), "http://someurl.com", "someref", "commitID")

        assert mock_call.call_count == 3
        assert mock_check_output.call_count == 1
