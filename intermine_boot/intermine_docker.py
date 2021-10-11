import docker
from pathlib import Path
import pickle as pkl
import subprocess
import shutil
import os
from git import Repo,cmd
import yaml
from intermine_boot import utils
import click
import re
import glob
import sys

# all docker containers created would be attached to this network
DOCKER_NETWORK_NAME = 'intermine_boot'

def _get_docker_user():
    return str(os.getuid()) + ':' + str(os.getgid())

# TODO configs when intermine_builder gets rewritten?
def _is_conf_same(path_to_config, options):
    conf_file_path = str(path_to_config) + '/.config'
    if not os.path.isfile(conf_file_path):
        return False

    config = pkl.load(open(conf_file_path, 'rb'))
    try:
        if (config['branch_name'] == options['im_branch']) and (
                config['repo_name'] == options['im_repo']):
            if options['source']:
                return config['source'] == options['source']
            return True
        else:
            return False
    except KeyError:
        return False


def _store_conf(path_to_config, options):
    config = {}
    config['branch_name'] = options['im_branch']
    config['repo_name'] = options['im_repo']
    if options['source']:
        config['source'] = options['source']

    f = open(path_to_config / '.config', 'wb')
    pkl.dump(config, f)
    return

def _get_mine_name(options, env):
    if options['mode'] in ['start', 'build'] and options['source']:
        return os.path.basename(os.path.abspath(options['source']))
    elif options['source']: # Likely path to an archive.
        prop_files = glob.glob(str(env['data_dir'] / 'data' / 'mine' / 'intermine' / '*.properties'))
        try:
            mine_name = os.path.basename(prop_files[0]).replace('.properties', '')
        except IndexError:
            mine_name = ''

        if not mine_name:
            click.echo('Failed to determine name of mine from ' + options['source'], err=True)
            click.echo('The archive is likely not supported', err=True)
            sys.exit(1)

        return mine_name
    else:
        return os.environ.get('MINE_NAME', 'biotestmine')


def _get_container_path():
    '''
    Returns the path to docker-intermine-gradle submodule.
    '''
    return Path(__file__).parent.absolute() / 'docker-intermine-gradle'

def _create_volumes(options, env):
    data_dir = env['data_dir'] / 'data'
    # make dirs if not exist
    Path(data_dir).mkdir(exist_ok=True)
    Path(data_dir / 'solr').mkdir(exist_ok=True)
    Path(data_dir / 'postgres').mkdir(exist_ok=True)
    Path(data_dir / 'mine').mkdir(exist_ok=True)
    Path(data_dir / 'mine' / 'dumps').mkdir(exist_ok=True)
    Path(data_dir / 'mine' / 'configs').mkdir(exist_ok=True)
    Path(data_dir / 'mine' / 'packages').mkdir(exist_ok=True)
    Path(data_dir / 'mine' / 'intermine').mkdir(exist_ok=True)
    Path(data_dir / 'mine' / _get_mine_name(options, env)).mkdir(exist_ok=True)
    Path(data_dir / 'mine' / '.intermine').mkdir(exist_ok=True)
    Path(data_dir / 'mine' / '.m2').mkdir(exist_ok=True)


def _create_network_if_not_exist(client):
    try:
        network = client.networks.get(DOCKER_NETWORK_NAME)
    except docker.errors.NotFound:
        network = client.networks.create(DOCKER_NETWORK_NAME)

    return network


def up(options, env, reuse=False):
    if (env['data_dir']).is_dir():
        if options['rebuild']:
            click.echo('Forced rebuild. Removing existing data if any...')
            shutil.rmtree(env['data_dir'])
        elif reuse:
            pass
        elif _is_conf_same(env['data_dir'], options):
            click.echo('Same configuration exists. Using existing data...')
        else:
            click.echo('Configuration change detected. Removing existing data if any...')
            shutil.rmtree(env['data_dir'])

    (env['data_dir']).mkdir(parents=True, exist_ok=True)

    _create_volumes(options, env)

    if options['mode'] in ['start', 'build'] and options['source']:
        click.echo('Source path is ' + os.path.abspath(options['source']))
        shutil.copytree(
            Path(
                options['source']),
                env['data_dir'] / 'data' / 'mine' / _get_mine_name(options, env),
                dirs_exist_ok=True)
    elif not options['source']:
        click.echo('No source path specified. Will build biotestmine.')

    client = docker.from_env()
    if options['build_images']:
        click.echo('Building images...')
        img_path = _get_container_path()
        tomcat_image = client.images.build(
            path=str(img_path / 'tomcat'), tag='tomcat', dockerfile='tomcat.Dockerfile')[0]
        solr_image = client.images.build(
            path=str(img_path / 'solr'), tag='solr', dockerfile='solr.Dockerfile')[0]
        postgres_image = client.images.build(
            path=str(img_path / 'postgres'), tag='postgres', dockerfile='postgres.Dockerfile')[0]
        intermine_builder_image = client.images.build(
            path=str(img_path / 'intermine_builder'), tag='builder', dockerfile='intermine_builder.Dockerfile')[0]
    else:
        click.echo('Pulling images...')
        tomcat_image = client.images.pull('intermine/tomcat:latest')
        solr_image = client.images.pull('intermine/solr:latest')
        postgres_image = client.images.pull('intermine/postgres:latest')
        intermine_builder_image = client.images.pull('intermine/builder:latest')

    docker_network = _create_network_if_not_exist(client)
    click.echo('Starting containers...')
    (tomcat, tomcat_status) = create_tomcat_container(client, tomcat_image)
    (solr, solr_status) = create_solr_container(client, solr_image, options, env)
    (postgres, postgres_status) = create_postgres_container(client, postgres_image, options, env)
    (intermine_builder, intermine_builder_status) = create_intermine_builder_container(
        client, intermine_builder_image, options, env)

    _store_conf(env['data_dir'], options)

    return (tomcat_status and solr_status and postgres_status and intermine_builder_status)


def _remove_container(client, container_name):
    try:
        container = client.containers.get(container_name)
    except docker.errors.NotFound:
        container = None

    if container is not None:
        container.remove(force=True)


def down(options, env):
    client = docker.from_env()
    _remove_container(client, 'intermine_tomcat')
    _remove_container(client, 'intermine_postgres')
    _remove_container(client, 'intermine_solr')
    _remove_container(client, 'intermine_builder')

    try:
        client.networks.get('intermine_boot').remove()
    except docker.errors.NotFound:
        pass


def create_archives(options, env):
    properties_file = env['data_dir'] / 'data' / 'mine' /  'intermine' / (_get_mine_name(options, env) + '.properties')

    archive_filename = ''
    try:
        title = ''
        version = ''
        with open(properties_file) as props:
            title_re = re.compile("^project\\.title=(.+)$")
            version_re = re.compile("^project\\.releaseVersion=(.+)$")

            for _, line in enumerate(props):
                if not title:
                    match_title = re.match(title_re, line)
                    if match_title:
                        title = match_title.group(1)

                if not version:
                    match_version = re.match(version_re, line)
                    if match_version:
                        version = match_version.group(1)

                if title and version:
                    break

            if title:
                archive_filename = title
                if version:
                    archive_filename += '-' + version

    except EnvironmentError:
        archive_filename = 'mine'

    archive = env['cwd'] / archive_filename
    target_dir = env['data_dir'] / 'data'
    created_archive = shutil.make_archive(archive, 'zip', root_dir=target_dir)

    click.echo('\n\nCreated archive ' + created_archive)

def create_tomcat_container(client, image, network_name=None):
    envs = {
        'MEM_OPTS': os.environ.get('MEM_OPTS', '-Xmx1g -Xms500m')
    }

    ports = {
        os.environ.get('TOMCAT_PORT', 8080): os.environ.get('TOMCAT_HOST_PORT', 9999)
    }

    click.echo('\n\nStarting Tomcat container...\n')
    tomcat_container = _start_container(
        client, image, name='intermine_tomcat', environment=envs, ports=ports,
        network=network_name or DOCKER_NETWORK_NAME, log_match='Server startup')

    return tomcat_container


def create_solr_container(client, image, options, env, mine_name=None, network_name=None):
    envs = {
        'MEM_OPTS': os.environ.get('MEM_OPTS', '-Xmx2g -Xms1g'),
        'MINE_NAME': mine_name or _get_mine_name(options, env)
    }

    user = _get_docker_user()

    data_dir = env['data_dir'] / 'data' / 'solr'
    volumes = {
        data_dir: {
            'bind': '/var/solr',
            'mode': 'rw'
        }
    }

    click.echo('\n\nStarting Solr container...\n')
    solr_container = _start_container(
        client, image, name='intermine_solr', environment=envs, user=user, volumes=volumes,
        network=network_name or DOCKER_NETWORK_NAME, log_match='Registered new searcher')

    return solr_container


def create_postgres_container(client, image, options, env, mine_name=None, network_name=None):
    envs = {
        'MINE_NAME': mine_name or _get_mine_name(options, env)
    }

    user = _get_docker_user()

    data_dir = env['data_dir'] / 'data' / 'postgres'
    volumes = {
        data_dir : {
            'bind': '/var/lib/postgresql/data',
            'mode': 'rw'
        }
    }

    click.echo('\n\nStarting Postgres container...\n')
    postgres_container = _start_container(
        client, image, name='intermine_postgres', environment=envs, user=user, volumes=volumes,
        network=network_name or DOCKER_NETWORK_NAME, log_match='autovacuum launcher started')

    return postgres_container


def create_intermine_builder_container(client, image, options, env):
    user = _get_docker_user()

    data_dir = env['data_dir'] / 'data'

    # TODO redo when intermine_builder gets rewritten?
    # would also be a good idea to always print the options/environment passed
    # to intermine_builder, or at least add an option to print them
    environment = {
        'SOLR_HOST': 'intermine_solr',
        'TOMCAT_HOST': 'intermine_tomcat',
        'PGHOST': 'intermine_postgres',
        'MINE_NAME': _get_mine_name(options, env),
        'MINE_REPO_URL': os.environ.get('MINE_REPO_URL', ''),
        'MEM_OPTS': os.environ.get('MEM_OPTS', '-Xmx2g -Xms1g'),
        'IM_DATA_DIR': os.environ.get('IM_DATA_DIR', ''),
        'FORCE_MINE_BUILD': 'true' if (
               options['mode'] in ['start', 'build'] and options['source'] and not _is_conf_same(env['data_dir'], options)
            ) else '' # 'false' is truthy while empty is falsey
    }

    if options['build_im']:
        IM_REPO_URL = os.environ.get('IM_REPO_URL', '')
        IM_REPO_BRANCH = os.environ.get('IM_REPO_BRANCH', '')
        environment['IM_REPO_URL'] = (
            IM_REPO_URL if IM_REPO_URL != '' else options['im_repo'])
        environment['IM_REPO_BRANCH'] = (
            IM_REPO_BRANCH if IM_REPO_BRANCH != '' else options['im_branch'])

    mine_path = env['data_dir'] / 'data' / 'mine'
    mine_name = _get_mine_name(options, env)

    # If we unpacked from a zip archive, these files could have lost their executable bit.
    for executable in ['gradlew', 'project_build', 'setup.sh']:
        try:
            os.chmod(mine_path / mine_name / executable, 0o775)
        except FileNotFoundError:
            pass

    volumes = {
        mine_path / 'dump': {
            'bind': '/home/intermine/intermine/dump',
            'mode': 'rw'
        },

        mine_path / 'configs': {
            'bind': '/home/intermine/intermine/configs',
            'mode': 'rw'
        },
        mine_path / 'packages': {
            'bind': '/home/intermine/.m2',
            'mode': 'rw'
        },
        mine_path / 'intermine': {
            'bind': '/home/intermine/.intermine',
            'mode': 'rw'
        },
        mine_path / mine_name: {
            'bind': '/home/intermine/intermine/' + mine_name,
            'mode': 'rw'
        }
    }

    click.echo('\n\nStarting Intermine container...\n\n')

    try:
        assert client.containers.get('intermine_postgres').status == 'running'
    except AssertionError:
        click.echo('Postgres container not running. Exiting...', err=True)
        exit(1)

    try:
        assert client.containers.get('intermine_tomcat').status == 'running'
    except AssertionError:
        click.echo('Tomcat container not running. Exiting...', err=True)
        exit(1)

    try:
        assert client.containers.get('intermine_solr').status == 'running'
    except AssertionError:
        click.echo('Solr container not running. Exiting...', err=True)
        exit(1)

    intermine_builder_container = _start_container(
        client, image, name='intermine_builder', user=user, environment=environment,
        volumes=volumes, network=DOCKER_NETWORK_NAME)

    return intermine_builder_container


def _start_container(
    client, image, name, user=None, environment=None, volumes=None,
        network=None, ports=None, log_match=None):
    status_code = True # A boolean value to indicate whether error occurs
    try:
        container = client.containers.run(
            image, name=name, user=user, environment=environment,
            volumes=volumes, network=network, detach=True, ports=ports)

        for log in container.logs(stream=True, timestamps=True):
            click.echo(log.decode(), nl=False)
            if log_match is not None and log_match in str(log):
                break
            if 'ERROR' in str(log):
                status_code = False
    except docker.errors.ImageNotFound as e:
        click.echo('docker image not found for %s: %s' % (container_name, e.msg), err=True)
        exit(1)
    except docker.errors.ContainerError as e:
        click.echo('Error while running container: %s' % e.msg, err=True)
        exit(1)

    return (container, status_code)
