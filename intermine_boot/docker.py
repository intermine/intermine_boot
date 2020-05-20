from pathlib import Path
import subprocess
import shutil
import os
from git import Repo,cmd
import yaml
from intermine_boot import utils
import boto3
from botocore.exceptions import ClientError


DOCKER_COMPOSE_REPO = 'https://github.com/intermine/docker-intermine-gradle'

ENV_VARS = ['env', 'UID='+str(os.geteuid()), 'GID='+str(os.getegid())]

#AWS credentials
AWS_CLOUD_CREDENTIALS = {
    's3': {
        'S3_BUCKET_NAME': '',
        'ACCESS_KEY': '',
        'SECRET_KEY': ''
    }
}

def _get_compose_path(options, env):
    work_dir = env['data_dir'] / 'docker'
    compose_file = 'dockerhub.docker-compose.yml'
    if options['build_images']:
        compose_file = 'local.docker-compose.yml'
    return work_dir / compose_file

def _create_volume_dirs(compose_path):
    with open(compose_path, 'r') as stream:
        compose_dict = yaml.safe_load(stream)

        for service in compose_dict['services']:
            service_dict = compose_dict['services'][service]

            if 'volumes' not in service_dict:
                continue

            volumes = service_dict['volumes']

            for volume in volumes:
                volume_dir = volume.split(':')[0]
                Path(compose_path.parent / volume_dir).mkdir(parents=True, exist_ok=True)

def up(options, env):
    compose_path = _get_compose_path(options, env)

    if compose_path.parent.is_dir():
        shutil.rmtree(compose_path.parent)

    Repo.clone_from(DOCKER_COMPOSE_REPO, compose_path.parent,
                    progress=utils.GitProgressPrinter())

    _create_volume_dirs(compose_path)

    option_vars = (['IM_REPO_URL='+options['im_repo'],
                    'IM_REPO_BRANCH='+options['im_branch']]
                   if options['build_im'] else [])

    if not options['build_images']:
        # Make sure dockerhub images are up-to-date.
        subprocess.run(['docker-compose',
                        '-f', compose_path.name,
                        'pull'],
                       check=True,
                       cwd=compose_path.parent)


    subprocess.run([*ENV_VARS, *option_vars,
                    'docker-compose',
                    '-f', compose_path.name,
                    'up', '-d'] +
                   (['--build', '--force-recreate']
                    if options['build_images'] else []),
                   check=True,
                   cwd=compose_path.parent)


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


def lsremote(url):
    remote_refs = {}
    g = cmd.Git()

    for ref in g.ls_remote(url).split('\n'):
        hash_ref_list = ref.split('\t')
        remote_refs[hash_ref_list[1]] = hash_ref_list[0]

    return remote_refs

def generate_version(options, env):
    if options['im_repo']!="":
        currhash = lsremote(options['im_repo'])
        version = options['im_repo']+"--"+options['im_branch']+"--"+currhash['HEAD']
    else:
        version = "latest_version"

    version = version.replace("https://github.com/", "")
    version = version.replace("/",".")

    return version

def upload_archives(options, env, method):
    if method == 's3':
        upload_archives_aws(options, env)
    else:
        print ('Method not implemented')
        raise (NotImplementedError)

def download_archives(options, env, method):
    if method == 's3':
        download_archives_aws(options, env)
    else:
        print ('Method not implemented')
        raise (NotImplementedError)

def upload_archives_aws(options, env):
    compose_path = _get_compose_path(options, env)
    postgres_archive_path = compose_path.parent / 'data' / 'postgres' / env['data_dir'] / 'postgres.zip'
    solr_archive_path = compose_path.parent / 'data' / 'solr' / env['data_dir'] / 'solr.zip'
    mine_archive_path = compose_path.parent / 'data' / 'biotestmine' / env['data_dir'] / 'biotestmine.zip'

    version = generate_version(options, env)

    s3 = boto3.client(
        's3', 
        aws_access_key_id=AWS_CLOUD_CREDENTIALS['s3']['ACCESS_KEY'], 
        aws_secret_access_key=AWS_CLOUD_CREDENTIALS['s3']['SECRET_KEY'])
    bucket = AWS_CLOUD_CREDENTIALS['s3']['S3_BUCKET_NAME']
    try:
        s3.upload_file(str(postgres_archive_path), bucket, str(version+'postgres.zip'))
        s3.upload_file(str(solr_archive_path), bucket, str(version+'solr.zip'))
        s3.upload_file(str(mine_archive_path), bucket, str(version+'biotestmine.zip'))
    except ClientError as error:
        print(error)

def download_archives_aws(options, env):
    compose_path = _get_compose_path(options, env)
    data_dir = compose_path.parent / 'data'
    postgres_data_dir = compose_path.parent / 'data' / 'postgres'
    solr_data_dir = compose_path.parent / 'data' / 'solr'
    mine_data_dir = compose_path.parent / 'data' / 'mine'
    version = generate_version(options, env)
    
    # download the archives
    s3 = boto3.client(
        's3', 
        aws_access_key_id=AWS_CLOUD_CREDENTIALS['s3']['ACCESS_KEY'], 
        aws_secret_access_key=AWS_CLOUD_CREDENTIALS['s3']['SECRET_KEY'])
    bucket = AWS_CLOUD_CREDENTIALS['s3']['S3_BUCKET_NAME']

    try:
        s3.download_file(bucket, str(version+'postgres.zip'), str(data_dir / str('postgres.zip')))
        s3.download_file(bucket, str(version+'solr.zip'), str(data_dir / str('solr.zip')))
        s3.download_file(bucket, str(version+'biotestmine.zip'), str(data_dir / str('mine.zip')))
    except ClientError as error:
        print(error)

    # unzip
    shutil.unpack_archive(str(data_dir / str('postgres.zip')), str(postgres_data_dir), 'zip')
    shutil.unpack_archive(str(data_dir / str('solr.zip')), str(solr_data_dir), 'zip')
    shutil.unpack_archive(str(data_dir / str('mine.zip')), str(mine_data_dir), 'zip')

    # delete the zips
    os.remove(str(data_dir / str('postgres.zip')))
    os.remove(str(data_dir / str('solr.zip')))
    os.remove(str(data_dir / str('mine.zip')))