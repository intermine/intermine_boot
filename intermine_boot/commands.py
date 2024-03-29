import subprocess
import sys
import re
import click
import shutil
import os
from intermine_boot import intermine_docker
from intermine_boot import archive

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

    try:
        status = intermine_docker.up(options, env)
    except:
        intermine_docker.down(options, env)
        raise

    if status:
        # TODO: Once we support building mines other than biotestmine, we should make this text dynamic.
        click.echo('Build completed. Visit http://localhost:9999/biotestmine to access your mine.')
    else:
        click.echo('Build unsuccessful. Please check error logs.')
        intermine_docker.down(options, env)

def stop(options, env):
    assert_docker(options, env)
    intermine_docker.down(options, env)

def build(options, env):
    assert_docker(options, env)

    try:
        status = intermine_docker.up(options, env)
    except:
        intermine_docker.down(options, env)
        raise

    if status:
        intermine_docker.down(options, env)
        intermine_docker.create_archives(options, env)
        # upload and download of files is possible only if you have valid access keys
        #archive.upload_archives(options, env, 's3')
        #docker.download_archives(options, env, 's3')
    else:
        click.echo('Build unsuccessful. Please check error logs.')
        intermine_docker.down(options, env)

def load(options, env):
    assert_docker(options, env)

    if not os.path.isfile(options['source']):
        click.echo('Please specify a SOURCE argument to an archive file.', err=True)
        sys.exit(1)

    if env['data_dir'].is_dir():
        shutil.rmtree(env['data_dir'])

    click.echo('Unpacking archive...')
    shutil.unpack_archive(options['source'], env['data_dir'] / 'data')

    try:
        status = intermine_docker.up(options, env, reuse=True)
    except:
        intermine_docker.down(options, env)
        raise

    if status:
        # TODO: Once we support building mines other than biotestmine, we should make this text dynamic.
        click.echo('Build completed. Visit http://localhost:9999/biotestmine to access your mine.')
    else:
        click.echo('Build unsuccessful. Please check error logs.')
        intermine_docker.down(options, env)

def clean(options, env):
    if env['data_dir'].is_dir():
        click.echo('Cleaning intermine_boot data')
        shutil.rmtree(env['data_dir'])

def _not_implemented(options, env):
    click.echo('This mode has not been implemented yet.')
    sys.exit(1)

def invoke(mode, options, env):
    modes = {
        'start': start,
        'stop': stop,
        'build': build,
        'load': load,
        'clean': clean
    }

    func = modes.get(mode, _not_implemented)
    return func(options, env)
