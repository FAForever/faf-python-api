import logging
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable

from faf import db
from faf.tools.fa.build_mod import build_mod
from faf.tools.fa.mods import parse_mod_info
from faf.tools.fa.update_version import update_exe_version
from flask import app
from pymysql.cursors import Cursor

from api import app
from api.deployment.git import checkout_repo, GitRepository
from api.error import ApiException, Error, ErrorCode

logger = logging.getLogger(__name__)


class DeploymentConfiguration(ABC):
    def __init__(self, repo: GitRepository, branch: str, autodeploy: bool):
        self.repo = repo  # type: GitRepository
        self._branch = branch  # type: str
        self._autodeploy = autodeploy  # type: bool

    @abstractmethod
    def deploy(self, deploy_id: str, commit_signature: str,
               callback_on_finished: Callable[[str, str, 'DeploymentConfiguration'], None]) -> None:
        pass

    def matches(self, repo_url: str, repo_name: str, branch: str, force_deploy: bool) -> bool:
        return self.repo.url == repo_url and self.repo.name == repo_name and self._branch == branch and (
            self._autodeploy or force_deploy)


class WebDeploymentConfiguration(DeploymentConfiguration):
    """
    WebDeploymentConfiguration is able to restart the webservices
    """

    def __init__(self, repo: GitRepository, branch: str, autodeploy: bool):
        super().__init__(repo, branch, autodeploy)

    def deploy(self, deploy_id: str, commit_signature: str,
               callback_on_finished: Callable[[str, str, 'DeploymentConfiguration'], None]) -> None:
        logger.info('Web-deployment started (repo=%s, branch=%s)', self.repo.name, self._branch)

        checkout_repo(Path(self.repo.path), self.repo.url, self._branch, commit_signature)
        restart_file = Path(self.repo.path, 'tmp/restart.txt')
        restart_file.touch()

        app.github.create_deployment_status(
            owner='FAForever',
            repo=self.repo.name,
            id=deploy_id,
            state='success',
            description='Deployment finished')

        deploy_message = 'Web-deployment finished (repo=%s, branch=%s)' % (self.repo.name, self._branch)
        logger.info(deploy_message)
        callback_on_finished(deploy_id, deploy_message, self)


class GameDeploymentConfiguration(DeploymentConfiguration):
    """
    GameDeploymentConfiguration is able to build a new game version and deploy it
    """

    def __init__(self, repo: GitRepository, branch: str, autodeploy: bool, featured_mod: str,
                 file_extension: str, allow_override: bool):
        super().__init__(repo, branch, autodeploy)
        self._featured_mod = featured_mod
        self._file_extension = file_extension
        self._allow_override = allow_override

    def deploy(self, deploy_id: str, commit_signature: str,
               callback_on_finished: Callable[[str, str, 'DeploymentConfiguration'], None]) -> None:
        logger.info('Game-deployment started (repo=%s, branch=%s)', self.repo.name, self._branch)

        app.github.create_deployment_status(
            owner=app.config['GIT_OWNER'],
            repo=self.repo.name,
            id=deploy_id,
            state='pending',
            description='Game-deployment started (repo=%s, branch=%s, featured_mod=%s)' % (
                self.repo.name, self._branch, self._featured_mod))

        checkout_repo(Path(self.repo.path), self.repo.url, self._branch, commit_signature)

        mod_info = parse_mod_info(Path(self.repo.path))  # Harvest data from mod_info.lua
        version = mod_info['version']
        temp_dir = TemporaryDirectory(prefix="deploy_%s_" % self._featured_mod)  # type: TemporaryDirectory

        with db.connection:
            cursor = db.connection.cursor()  # type: Cursor

            cursor.execute(
                "select count(*) from updates_{}_files where version = %s".format(self._featured_mod), version)
            file_count = cursor.fetchone()

            if file_count[0] > 0 and not self._allow_override:
                raise ApiException([Error(ErrorCode.DEPLOYMENT_ERROR,
                                          "Configuration prohibits override (repo=%s, branch=%s)" % (
                                              self.repo.name, self._branch))])

            # TODO: move this into separate process to prevent api from blocking

            logger.debug('Begin building mod (this may take a while)')
            files = build_mod(self.repo.path, mod_info,
                              Path(temp_dir.name))  # Build the mod from the fileset we just checked out
            logger.debug('Build result: {}'.format(files))

            # Create the storage path for the version files. This is where the zips will be moved to from temp
            deploy_path = Path(app.config['GAME_DEPLOY_PATH'], 'updates_%s_files' % self._featured_mod)
            deploy_path.mkdir(parents=True, exist_ok=True)

            # Create a new ForgedAlliance.exe compatible with the new version
            logger.debug('Create version of ForgedAlliance.exe')
            base_game_exe = Path(app.config['BASE_GAME_EXE'])
            update_exe_version(base_game_exe, deploy_path, version)

            logger.debug('Deploying %s to %s', self._featured_mod, deploy_path)

            if file_count[0] > 0 and self._allow_override:
                logging.info("Overwriting current version %s", version)
                cursor.execute(
                    "delete from updates_{}_files where version = %s;".format(self._featured_mod), version)

            for file in files:
                # Organise the files needed into their final setup and pack as .zip
                # TODO: Check client can handle NX# being dealt with here in API
                destination = deploy_path / (file['filename'] + '_0.' + str(version) + self._file_extension)
                logger.debug('Deploying %s to %s', file, destination)
                shutil.move(str(file['path']), str(destination))

                # Update the database with the new mod
                cursor.execute('insert into updates_{}_files '
                               '(fileId, version, md5, name) '
                               'values (%s,%s,%s,%s)'.format(self._featured_mod),
                               (file['id'], version, file['md5'], destination.name))

        deploy_message = 'Game-Deployment completed (repo=%s, branch=%s, featured_mod=%s)' % (
            self.repo.url, self._branch, self._featured_mod)
        logger.info(deploy_message)
        temp_dir.cleanup()
        callback_on_finished(deploy_id, deploy_message, self)
