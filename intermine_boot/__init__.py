import subprocess
import sys
import re
import click
from xdg import (XDG_DATA_HOME)
from intermine_boot import docker, commands

MODE_OPTIONS = ['start', 'stop', 'build', 'load', 'clean']
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
@click.option('--rebuild', is_flag=True, default=False, help='Rebuild your mine from scratch even if it already exists.')
def cli(**options):
    """Here will be a description of this script.
    Remember to also document modes and targets.
    """

    data_dir = XDG_DATA_HOME / 'intermine_boot'
    if not data_dir.is_dir():
        data_dir.mkdir()
    env = {
        'data_dir': data_dir
    }

    commands.invoke(options['mode'], options, env)
