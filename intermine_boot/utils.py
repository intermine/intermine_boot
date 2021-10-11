import subprocess
import re
import sys
import click
from git import RemoteProgress


def op_code_to_label(op_code):
    if op_code == 33:
        return 'Receiving objects:'
    if op_code == 65:
        return 'Resolving deltas:'
    return ''


class GitProgressPrinter(RemoteProgress):
    progress = None

    def update(self, op_code, cur_count, max_count=100.0, message=''):
        if cur_count <= 1:
            self.progress = click.progressbar(length=int(max_count),
                                              label=op_code_to_label(op_code))
        self.progress.pos = cur_count
        self.progress.update(0)

        if cur_count == max_count:
            self.progress.render_finish()


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
