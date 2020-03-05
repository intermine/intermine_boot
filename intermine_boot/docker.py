from pathlib import Path
import tempfile
import subprocess
import shutil
import os
import click
import yaml
from git import Repo
from xdg import (XDG_DATA_HOME)
from intermine_boot import utils

DOCKER_COMPOSE_REPO = 'https://github.com/uosl/docker-intermine-gradle'

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


def create_volume_dirs(compose_path):
    with open(compose_path, 'r') as stream:
        compose_dict = yaml.safe_load(stream)

        for service in compose_dict['services']:
            service_dict = compose_dict['services'][service]

            if 'volumes' not in service_dict:
                continue

            volumes = service_dict['volumes']

            for volume in volumes:
                volume_dir = volume.split(':')[0]
                Path(compose_path.parent / volume_dir).mkdir(parents=True, exist_ok=True)


def main(**options):
    data_dir = XDG_DATA_HOME / 'intermine_boot'
    work_dir = data_dir / 'docker'
    compose_config = 'dockerhub.docker-compose.yml'
    if options['build_images']:
        compose_config = 'local.docker-compose.yml'
    config_path = work_dir / compose_config

    if not data_dir.is_dir():
        data_dir.mkdir()

    fresh_build = not work_dir.is_dir()

    if fresh_build:
        Repo.clone_from(DOCKER_COMPOSE_REPO, work_dir,
                        progress=utils.GitProgressPrinter())
        create_volume_dirs(config_path)
    else:
        if options['rebuild']:
            shutil.rmtree(work_dir)

            Repo.clone_from(DOCKER_COMPOSE_REPO, work_dir,
                            progress=utils.GitProgressPrinter())
            create_volume_dirs(config_path)

    up(config_path, build=options['build_images'])

    if fresh_build:
        # This command will print the logs from intermine_builder and exit
        # once it finishes building (blocking until then).
        subprocess.run(['docker-compose',
                        '-f', compose_config,
                        'logs', '-f', 'intermine_builder'],
                       check=True,
                       cwd=work_dir)

    if options['mode'] == 'build':
        down(config_path)

        postgres_archive = data_dir / 'postgres'
        postgres_data_dir = work_dir / 'data' / 'postgres'
        shutil.make_archive(postgres_archive, 'xztar', root_dir=postgres_data_dir)

        solr_archive = data_dir / 'solr'
        solr_data_dir = work_dir / 'data' / 'solr'
        shutil.make_archive(solr_archive, 'xztar', root_dir=solr_data_dir)
    else:
        # Store the docker-compose file so we can stop it later.
        shutil.copy(config_path, (data_dir / 'docker-compose.yml'))
