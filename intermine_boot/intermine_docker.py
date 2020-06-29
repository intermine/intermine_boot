import docker
from pathlib import Path
import pickle as pkl
import subprocess
import shutil
import os
from git import Repo,cmd
import yaml
from intermine_boot import utils


DOCKER_COMPOSE_REPO = 'https://github.com/intermine/docker-intermine-gradle'

ENV_VARS = ['env', 'UID='+str(os.geteuid()), 'GID='+str(os.getegid())]

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
            return True
        else:
            return False
    except KeyError:
        return False


def _store_conf(path_to_config, options):
    config = {}
    config['branch_name'] = options['im_branch']
    config['repo_name'] = options['im_repo']

    f = open(path_to_config / '.config', 'wb')
    pkl.dump(config, f)
    return


def _get_compose_path(options, env):
    work_dir = env['data_dir'] / 'docker'
    compose_file = 'dockerhub.docker-compose.yml'
    if options['build_images']:
        compose_file = 'local.docker-compose.yml'
    return work_dir / compose_file

def _create_volumes(env):
    data_dir = env['data_dir'] / 'docker' / 'data'
    os.mkdir(data_dir)
    os.mkdir(data_dir / 'solr')
    os.mkdir(data_dir / 'postgres')
    os.mkdir(data_dir / 'mine')
    os.mkdir(data_dir / 'mine' / 'dumps')
    os.mkdir(data_dir / 'mine' / 'configs')
    os.mkdir(data_dir / 'mine' / 'packages')
    os.mkdir(data_dir / 'mine' / 'intermine')
    os.mkdir(data_dir / 'mine' / 'biotestmine')
    os.mkdir(data_dir / 'mine' / '.intermine')
    os.mkdir(data_dir / 'mine' / '.m2')

def up(options, env):
    compose_path = _get_compose_path(options, env)

    same_conf_exist = False
    if compose_path.parent.is_dir():
        if _is_conf_same(env['data_dir'], options):
            print ('Same configuration exist. Running local compose file...') 
            same_conf_exist = True
        else:
            print ('Configuration change detected. Downloading compose file...')
            shutil.rmtree(compose_path.parent)
    
    if not same_conf_exist:
        print ('Same conf not found...', compose_path.parent)
        Repo.clone_from(DOCKER_COMPOSE_REPO, compose_path.parent, 
                    progress=utils.GitProgressPrinter())

    _create_volumes(env)

    option_vars = (['IM_REPO_URL='+options['im_repo'],
                    'IM_REPO_BRANCH='+options['im_branch']]
                   if options['build_im'] else [])

    client = docker.from_env()
    if options['build_images']:
        print ('Building images...')
        img_path = compose_path.parent
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

    print ('Starting containers...')
    tomcat_container = create_tomcat_container(client, tomcat_image)
    solr_container = create_solr_container(client, solr_image, env)
    postgres_container = create_postgres_container(client, postgres_image, env)
    intermine_builder_container = create_intermine_builder_container(
        client, intermine_builder_image, env)

    print('TOMCAT........')
    print(tomcat_container.logs())
    print('\n\n\nSOLR............')
    print(solr_container.logs())
    print('\n\n\nPOSTGRES...........')
    print(postgres_container.logs())
    print('\n\n\nINTERMINE...........')
    print(intermine_builder_container.logs())
    
    _store_conf(env['data_dir'], options)


def down(options, env):
    compose_path = _get_compose_path(options, env)
    subprocess.run([*ENV_VARS,
                    'docker-compose',
                    '-f', compose_path.name,
                    'down'],
                   check=True,
                   cwd=compose_path.parent)


def monitor_builder(options, env):
    compose_path = _get_compose_path(options, env)
    # This command will print the logs from intermine_builder and exit
    # once it finishes building (blocking until then).
    subprocess.run(['docker-compose',
                    '-f', compose_path.name,
                    'logs', '-f', 'intermine_builder'],
                   check=True,
                   cwd=compose_path.parent)


def create_archives(options, env):
    compose_path = _get_compose_path(options, env)

    postgres_archive = env['data_dir'] / 'postgres'
    postgres_data_dir = compose_path.parent / 'data' / 'postgres'
    shutil.make_archive(postgres_archive, 'zip', root_dir=postgres_data_dir)

    solr_archive = env['data_dir'] / 'solr'
    solr_data_dir = compose_path.parent / 'data' / 'solr'
    shutil.make_archive(solr_archive, 'zip', root_dir=solr_data_dir)

    mine_archive = env['data_dir'] / 'biotestmine'
    mine_data_dir = compose_path.parent / 'data' / 'mine' / 'biotestmine'
    shutil.make_archive(mine_archive, 'zip', root_dir=mine_data_dir)


def create_tomcat_container(client, image):
    envs = {
        'MEM_OPTS': os.environ.get('MEM_OPTS', '-Xmx1g -Xms500m')
    }

    ports = {
        8080: 9999
    }

    print ('\n\nStarting Tomcat container...\n')
    tomcat_container = client.containers.run(
        image, name='tomcat_container', environment=envs, ports=ports,
        detach=True)

    for log in tomcat_container.logs(stream=True, timestamps=True):
        print(log)
        if 'Server startup' in str(log):
            break
    
    return tomcat_container


def create_solr_container(client, image, env):
    envs = {
        'MEM_OPTS': os.environ.get('MEM_OPTS', '-Xmx2g -Xms1g'),
        'MINE_NAME': os.environ.get('MINE_NAME', 'biotestmine')
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
    solr_container = client.containers.run(
        image, name='solr_container', environment=envs, user=user, volumes=volumes,
        detach=True)

    for log in solr_container.logs(stream=True, timestamps=True):
        print (log)
        if 'Registered new searcher' in str(log):
            break

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
    postgres_container = client.containers.run(
        image, name='postgres_container', user=user, volumes=volumes,
        detach=True)

    for log in postgres_container.logs(stream=True, timestamps=True):
        print (log)
        if 'autovacuum launcher started' in str(log):
            break

    return postgres_container


def create_intermine_builder_container(client, image, env):
    user = _get_docker_user()

    data_dir = env['data_dir'] / 'docker' / 'data'

    environment = {
        'MINE_NAME': os.environ.get('MINE_NAME', 'biotestmine'),
        'MINE_REPO_URL': os.environ.get('MINE_REPO_URL', ''),
        'IM_DATA_DIR': env['data_dir'],
        'MEM_OPTS': os.environ.get('MEM_OPTS', '-Xmx2g -Xms1g'),
        'IM_REPO_URL': os.environ.get('IM_REPO_URL', ''),
        'IM_REPO_BRANCH': os.environ.get('IM_REPO_BRANCH', '')
    }

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
        mine_path / 'biotestmine': {
            'bind': '/home/intermine/intermine/biotestmine',
            'mode': 'rw'
        }
    }

    print ('\n\nStarting Intermine container...\n\n')
    intermine_builder_container = client.containers.run(
        image, name='intermine_container', user=user, environment=environment,
        volumes=volumes, detach=True)

    for log in intermine_builder_container.logs(stream=True, timestamps=True):
        print (log)

    return intermine_builder_container
