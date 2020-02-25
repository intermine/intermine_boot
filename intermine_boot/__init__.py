import subprocess
import sys
import re
import click
from xdg import (XDG_DATA_HOME)
from intermine_boot import build_intermine, docker_compose

MODE_OPTIONS = ['start', 'stop', 'build', 'load', 'setup']
TARGET_OPTIONS = ['local']


@click.command()
@click.argument('mode', type=click.Choice(MODE_OPTIONS, case_sensitive=False))
@click.argument('target', type=click.Choice(TARGET_OPTIONS, case_sensitive=False))
@click.option('--ci', is_flag=True, default=False, help='Run in CI mode.')
@click.option('--build-im', is_flag=True, default=False, help='Perform a build of InterMine prior to building the instance.')
@click.option('--im-repo', default='https://github.com/intermine/intermine', help='Build InterMine from this Git repository. Needs to be used with `--build-im`.')
@click.option('--im-branch', default='dev', help='Use this branch when building InterMine. Needs to be used with `--build-im`.')
@click.option('--im-version', help='Use a specific version of InterMine. Has no effect when used with `--build-im`, in which case the built version will be used.')
@click.option('--bio-version', help='Use a specific version of InterMine\'s bio packages. Has no effect when used with `--build-im`, in which case the built version will be used.')
@click.option('--build-images', is_flag=True, default=False, help='Build Docker images locally instead of using prebuilt images from Docker Hub.')
def cli(mode, target,
        ci, build_im, im_repo, im_branch, im_version, bio_version,
        build_images):
    """Here will be a description of this script.
    Remember to also document modes and targets.
    """

    docker_info = subprocess.run(['docker', 'info'],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
    if docker_info.returncode != 0:
        out = docker_info.stdout.decode('utf-8')

        permission_denied = re.search(r'permission denied', out, re.IGNORECASE)
        cannot_connect = re.search(r'cannot connect', out, re.IGNORECASE)

        if permission_denied:
            click.echo('You do not have permission to access the docker daemon.', err=True)
            click.echo('Please run `sudo groupadd docker` followed by `sudo usermod -aG docker $USER`, then log out and log back in. See https://docs.docker.com/install/linux/linux-postinstall/ for more information.')
            sys.exit(1)
        elif cannot_connect:
            click.echo('You don\'t seem to have a running docker daemon.', err=True)
            click.echo('See https://docs.docker.com/install/ for instructions on installing the Docker Engine. If you\'re using a Linux distro, you can install docker with your package manager.')
            sys.exit(1)
        else:
            click.echo(out, err=True)
            sys.exit(docker_info.returncode)

    built_versions = {
        'im_version': im_version,
        'bio_version': bio_version
    }

    if build_im:
        built_versions = build_intermine.main(im_repo=im_repo,
                                              im_branch=im_branch)
    if mode in ['start', 'build', 'load']:
        docker_compose.main(mode, versions=built_versions, build_images=build_images)

    if mode == 'stop':
        config_path = XDG_DATA_HOME / 'intermine_boot' / 'docker-compose.yml'

        if config_path.is_file():
            docker_compose.down(config_path)
            config_path.unlink()
