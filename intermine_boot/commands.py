import subprocess
import sys
import re
import click
from intermine_boot import docker

def assert_docker(options, env):
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


def start(options, env):
    assert_docker(options, env)
    docker.up(options, env)
    docker.monitor_builder(options, env)
    click.echo('Build completed. Visit http://localhost:9999/biotestmine to access your mine.')
    # TODO: Once we support building mines other than biotestmine, we should make this text dynamic.

def stop(options, env):
    assert_docker(options, env)
    docker.down(options, env)

def build(options, env):
    assert_docker(options, env)
    docker.up(options, env)
    docker.monitor_builder(options, env)
    docker.down(options, env)
    docker.create_archives(options, env)

def _not_implemented(options, env):
    click.echo('This mode has not been implemented yet.')
    sys.exit(1)

def invoke(mode, options, env):
    modes = {
        'start': start,
        'stop': stop,
        'build': build
    }

    func = modes.get(mode, _not_implemented)
    return func(options, env)
