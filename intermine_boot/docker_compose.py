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

        work_dir = os.path.join(tmpdir, 'docker-intermine-gradle')

        Repo.clone_from(DOCKER_COMPOSE_REPO, work_dir,
                        progress=utils.GitProgressPrinter())

        compose_config = 'dockerhub.docker-compose.yml'
        if build_images:
            compose_config = 'local.docker-compose.yml'

        config_path = os.path.join(work_dir, compose_config)

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

            postgres_archive = os.path.join(tmpdir, 'postgres')
            postgres_data_dir = os.path.join(work_dir, 'data', 'postgres')
            shutil.make_archive(postgres_archive, 'xztar', root_dir=postgres_data_dir)

            solr_archive = os.path.join(tmpdir, 'solr')
            solr_data_dir = os.path.join(work_dir, 'data', 'solr')
            shutil.make_archive(solr_archive, 'xztar', root_dir=solr_data_dir)
        else:
            # Store the docker-compose file so we can stop it later.
            storage_dir = os.path.join(
                os.path.expanduser('~'),
                '.intermine_boot'
            )
            if not os.path.isdir(storage_dir):
                os.mkdir(storage_dir)
            shutil.copy(config_path,
                        os.path.join(storage_dir, 'docker-compose.yml'))
