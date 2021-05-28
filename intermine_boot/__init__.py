import subprocess
import sys
import re
import click
from xdg import (XDG_DATA_HOME)
from intermine_boot import commands
import pathlib
import pkg_resources

MODE_OPTIONS = ['start', 'stop', 'build', 'load', 'clean']
TARGET_OPTIONS = ['local']


@click.command()
@click.version_option(pkg_resources.require('intermine_boot')[0].version)
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
@click.option('--datapath-im', default=None, help='Path of the mine folder.')
def cli(**options):
    """Spin up containers for building and running an InterMine server.

Modes:

start - Start containers for building an InterMine. Once finished, the server will continue running until stopped. Defaults to Biotestmine, and will reuse data from a previously built mine if identical.

stop - Stop and remove any running containers used to build and run an InterMine.

Targets:

local - Use the local docker daemon as host for the containers.
    """

    data_dir = XDG_DATA_HOME / 'intermine_boot'
    if not data_dir.is_dir():
        data_dir.mkdir(parents=True)
    env = {
        'data_dir': data_dir
    }

    commands.invoke(options['mode'], options, env)
