import docker
from pathlib import Path
import pickle as pkl
import subprocess
import shutil
import os
from git import Repo,cmd
import yaml
from intermine_boot import utils

# all docker containers created would be attached to this network
DOCKER_NETWORK_NAME = 'intermine_boot'

def _get_docker_user():
    return str(os.getuid()) + ':' + str(os.getgid())

def _is_conf_same(path_to_config, options):
    conf_file_path = str(path_to_config) + '/.config'
    if not os.path.isfile(conf_file_path):
        return False

    config = pkl.load(open(conf_file_path, 'rb'))
    try:
        if (config['branch_name'] == options['im_branch']) and (
                config['repo_name'] == options['im_repo']):
            if options['datapath_im']:
                return config['datapath_im'] == options['datapath_im']
            return True
        else:
            return False
    except KeyError:
        return False


def _store_conf(path_to_config, options):
    config = {}
    config['branch_name'] = options['im_branch']
    config['repo_name'] = options['im_repo']
    if options['datapath_im']:
        config['datapath_im'] = options['datapath_im']

    f = open(path_to_config / '.config', 'wb')
    pkl.dump(config, f)
    return


def _get_mine_name(options):
    if options['datapath_im']:
        return options['datapath_im'].strip('/').split('/')[-1]
    else:
        return os.environ.get('MINE_NAME', 'biotestmine')


def _get_container_path():
    '''
    Returns the path to docker-intermine-gradle submodule.
    '''
    return Path(__file__).parent.parent.absolute() / 'docker-intermine-gradle'

def _create_volumes(env, options):
    data_dir = env['data_dir'] / 'docker' / 'data'
    # make dirs if not exist
    Path(data_dir).mkdir(exist_ok=True)
    Path(data_dir / 'solr').mkdir(exist_ok=True)
    Path(data_dir / 'postgres').mkdir(exist_ok=True)
    Path(data_dir / 'mine').mkdir(exist_ok=True)
    Path(data_dir / 'mine' / 'dumps').mkdir(exist_ok=True)
    Path(data_dir / 'mine' / 'configs').mkdir(exist_ok=True)
    Path(data_dir / 'mine' / 'packages').mkdir(exist_ok=True)
    Path(data_dir / 'mine' / 'intermine').mkdir(exist_ok=True)
    Path(data_dir / 'mine' / _get_mine_name(options)).mkdir(exist_ok=True)
    Path(data_dir / 'mine' / '.intermine').mkdir(exist_ok=True)
    Path(data_dir / 'mine' / '.m2').mkdir(exist_ok=True)


def _create_network_if_not_exist(client):
    try:
        network = client.networks.get(DOCKER_NETWORK_NAME)
    except docker.errors.NotFound:
        network = client.networks.create(DOCKER_NETWORK_NAME)

    return network


def up(options, env):
    same_conf_exist = False
    if (env['data_dir'] / 'docker').is_dir():
        if _is_conf_same(env['data_dir'], options):
            print ('Same configuration exist. Using existing data...')
            same_conf_exist = True
        else:
            print ('Configuration change detected. Removing existing data if any...')
            shutil.rmtree(env['data_dir'])

    if not same_conf_exist:
        (env['data_dir'] / 'docker/').mkdir(parents=True, exist_ok=True)

    _create_volumes(env, options)

    if options['datapath_im']:
        print ('data path is ' + options['datapath_im'])
        shutil.copytree(
            Path(
                options['datapath_im']),
                env['data_dir'] / 'docker' / 'data' / 'mine' / _get_mine_name(options),
                dirs_exist_ok=True)

    client = docker.from_env()
    if options['build_images']:
        print ('Building images...')
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
        print ('Pulling images...')
        tomcat_image = client.images.pull('intermine/tomcat:latest')
        solr_image = client.images.pull('intermine/solr:latest')
        postgres_image = client.images.pull('intermine/postgres:latest')
        intermine_builder_image = client.images.pull('intermine/builder:latest')

    docker_network = _create_network_if_not_exist(client)
    print ('Starting containers...')
    tomcat = create_tomcat_container(client, tomcat_image)
    solr = create_solr_container(client, solr_image, env, options)
    postgres = create_postgres_container(client, postgres_image, env)
    intermine_builder = create_intermine_builder_container(
        client, intermine_builder_image, env, options)

    _store_conf(env['data_dir'], options)


def _remove_container(client, container_name):
    try:
        container = client.containers.get(container_name)
    except docker.errors.NotFound:
        container = None

    if container is not None:
        container.remove(force=True)


def down(options, env):
    client = docker.from_env()
    _remove_container(client, 'tomcat')
    _remove_container(client, 'postgres')
    _remove_container(client, 'solr')
    _remove_container(client, 'intermine_builder')

    try:
        client.networks.get('intermine_boot').remove()
    except docker.errors.NotFound:
        pass


def create_archives(options, env):
    postgres_archive = env['data_dir'] / 'postgres'
    postgres_data_dir = env['data_dir'] / 'data' / 'postgres'
    shutil.make_archive(postgres_archive, 'zip', root_dir=postgres_data_dir)

    solr_archive = env['data_dir'] / 'solr'
    solr_data_dir = env['data_dir'] / 'data' / 'solr'
    shutil.make_archive(solr_archive, 'zip', root_dir=solr_data_dir)

    mine_archive = env['data_dir'] / _get_mine_name(options)
    mine_data_dir = env['data_dir'] / 'data' / 'mine' / _get_mine_name(options)
    shutil.make_archive(mine_archive, 'zip', root_dir=mine_data_dir)


def create_tomcat_container(client, image):
    envs = {
        'MEM_OPTS': os.environ.get('MEM_OPTS', '-Xmx1g -Xms500m')
    }

    ports = {
        os.environ.get('TOMCAT_PORT', 8080): os.environ.get('TOMCAT_HOST_PORT', 9999)
    }

    print ('\n\nStarting Tomcat container...\n')
    tomcat_container = _start_container(
        client, image, name='tomcat', environment=envs, ports=ports,
        network=DOCKER_NETWORK_NAME, log_match='Server startup')

    return tomcat_container


def create_solr_container(client, image, env, options):
    envs = {
        'MEM_OPTS': os.environ.get('MEM_OPTS', '-Xmx2g -Xms1g'),
        'MINE_NAME': _get_mine_name(options)
    }

    user = _get_docker_user()

    data_dir = env['data_dir'] / 'docker' / 'data' / 'solr'
    volumes = {
        data_dir: {
            'bind': '/var/solr',
            'mode': 'rw'
        }
    }

    print('\n\nStarting Solr container...\n')
    solr_container = _start_container(
        client, image, name='solr', environment=envs, user=user, volumes=volumes,
        network=DOCKER_NETWORK_NAME, log_match='Registered new searcher')

    return solr_container


def create_postgres_container(client, image, env):
    user = _get_docker_user()
    data_dir = env['data_dir'] / 'docker' / 'data' / 'postgres'
    volumes = {
        data_dir : {
            'bind': '/var/lib/postgresql/data',
            'mode': 'rw'
        }
    }

    print ('\n\nStarting Postgres container...\n')
    postgres_container = _start_container(
        client, image, name='postgres', user=user, volumes=volumes,
        network=DOCKER_NETWORK_NAME, log_match='autovacuum launcher started')

    return postgres_container


def create_intermine_builder_container(client, image, env, options):
    user = _get_docker_user()

    data_dir = env['data_dir'] / 'docker' / 'data'

    environment = {
        'MINE_NAME': _get_mine_name(options),
        'MINE_REPO_URL': os.environ.get('MINE_REPO_URL', ''),
        'MEM_OPTS': os.environ.get('MEM_OPTS', '-Xmx2g -Xms1g'),
        'IM_DATA_DIR': os.environ.get('IM_DATA_DIR', ''),
        'FORCE_MINE_BUILD': 'true' if options['datapath_im'] else 'false'
    }

    if options['build_im']:
        IM_REPO_URL = os.environ.get('IM_REPO_URL', '')
        IM_REPO_BRANCH = os.environ.get('IM_REPO_BRANCH', '')
        environment['IM_REPO_URL'] = (
            IM_REPO_URL if IM_REPO_URL != '' else options['im_repo'])
        environment['IM_REPO_BRANCH'] = (
            IM_REPO_BRANCH if IM_REPO_BRANCH != '' else options['im_branch'])

    mine_path = env['data_dir'] / 'docker' / 'data' / 'mine'

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
        mine_path / _get_mine_name(options): {
            'bind': '/home/intermine/intermine/' + _get_mine_name(options),
            'mode': 'rw'
        }
    }

    print ('\n\nStarting Intermine container...\n\n')

    try:
        assert client.containers.get('postgres').status == 'running'
    except AssertionError:
        print ('Postgres container not running. Exiting...')
        exit(1)

    try:
        assert client.containers.get('tomcat').status == 'running'
    except AssertionError:
        print ('Tomcat container not running. Exiting...')
        exit(1)

    try:
        assert client.containers.get('solr').status == 'running'
    except AssertionError:
        print ('Solr container not running. Exiting...')

    intermine_builder_container = _start_container(
        client, image, name='intermine_builder', user=user, environment=environment,
        volumes=volumes, network=DOCKER_NETWORK_NAME)

    return intermine_builder_container


def _start_container(client, image, name, user=None, environment=None, volumes=None, network=None, ports=None, log_match=None):
    try:
        container = client.containers.run(
            image, name=name, user=user, environment=environment,
            volumes=volumes, network=network, detach=True, ports=ports)

        for log in container.logs(stream=True, timestamps=True):
            print (log.decode())
            if log_match is not None and log_match in str(log):
                break
    except docker.errors.ImageNotFound as e:
        print ('docker image not found for %s ' % container_name, e.msg)
        exit(1)
    except docker.errors.ContainerError as e:
        print ('Error while running container ', e.msg)
        exit(1)

    return container
