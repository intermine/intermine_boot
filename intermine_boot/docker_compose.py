from pathlib import Path
import tempfile
import subprocess
import shutil
import os
import click
from git import Repo
from xdg import (XDG_DATA_HOME)
from intermine_boot import utils

DOCKER_COMPOSE_REPO = 'https://github.com/intermine/docker-intermine-gradle'

ENV_VARS = ['env', 'UID='+str(os.geteuid()), 'GID='+str(os.getegid())]

def up(compose_path, build=False):
    subprocess.run([*ENV_VARS,
                    'docker-compose',
                    '-f', compose_path.name,
                    'up', '-d'] +
                   (['--build', '--force-recreate'] if build else []),
                   check=True,
                   cwd=compose_path.parent)


def down(compose_path):
    subprocess.run([*ENV_VARS,
                    'docker-compose',
                    '-f', compose_path.name,
                    'down'],
                   check=True,
                   cwd=compose_path.parent)


def main(mode, versions, build_images):
    with tempfile.TemporaryDirectory(prefix='intermine_boot_') as tmpdir:
        tmpdir = Path(tmpdir)

        work_dir = tmpdir / 'docker-intermine-gradle'

        Repo.clone_from(DOCKER_COMPOSE_REPO, work_dir,
                        progress=utils.GitProgressPrinter())

        compose_config = 'dockerhub.docker-compose.yml'
        if build_images:
            compose_config = 'local.docker-compose.yml'

        config_path = work_dir / compose_config

        up(config_path, build=build_images)

        # This command will print the logs from intermine_builder and exit
        # once it finishes building (blocking until then).
        subprocess.run(['docker-compose',
                        '-f', compose_config,
                        'logs', '-f', 'intermine_builder'],
                       check=True,
                       cwd=work_dir)

        if mode == 'build':
            down(config_path)

            # TODO might not work due to user ids -- need to be tested
            # We'll either have to make the docker containers use the same
            # user id as the user, or run chown and chmod.

            postgres_archive = tmpdir / 'postgres'
            postgres_data_dir = work_dir / 'data' / 'postgres'
            shutil.make_archive(postgres_archive, 'xztar', root_dir=postgres_data_dir)

            solr_archive = tmpdir / 'solr'
            solr_data_dir = work_dir / 'data' / 'solr'
            shutil.make_archive(solr_archive, 'xztar', root_dir=solr_data_dir)
        else:
            # Store the docker-compose file so we can stop it later.
            storage_dir = XDG_DATA_HOME / 'intermine_boot'
            storage_dir.mkdir(exist_ok=True)
            shutil.copy(config_path, (storage_dir / 'docker-compose.yml'))
