import os
import tempfile
import subprocess
import shutil
import click
from git import Repo
from intermine_boot import utils

DOCKER_COMPOSE_REPO = 'https://github.com/intermine/docker-intermine-gradle'


def up(config_path, build=False):
    compose_config = os.path.basename(config_path)
    compose_dir = os.path.dirname(config_path)

    subprocess.run(['docker-compose',
                    '-f', compose_config,
                    'up', '-d'] +
                   (['--build', '--force-recreate'] if build else []),
                   check=True,
                   cwd=compose_dir)


def down(config_path):
    compose_config = os.path.basename(config_path)
    compose_dir = os.path.dirname(config_path)

    subprocess.run(['docker-compose',
                    '-f', compose_config,
                    'down'],
                   check=True,
                   cwd=compose_dir)


def main(mode, versions, build_images):
    with tempfile.TemporaryDirectory(prefix='intermine_boot_') as tmpdir:

        docker_dir = os.path.join(tmpdir, 'docker-intermine-gradle')

        Repo.clone_from(DOCKER_COMPOSE_REPO, docker_dir,
                        progress=utils.GitProgressPrinter())

        compose_config = 'dockerhub.docker-compose.yml'
        if build_images:
            compose_config = 'local.docker-compose.yml'

        config_path = os.path.join(docker_dir, compose_config)

        up(config_path, build=build_images)

        if mode == 'build':
            down(config_path)
        else:
            storage_dir = os.path.join(
                os.path.expanduser('~'),
                '.intermine_boot'
            )
            if not os.path.isdir(storage_dir):
                os.mkdir(storage_dir)
            shutil.copy(config_path,
                        os.path.join(storage_dir, 'docker-compose.yml'))
