import boto3
from git import Repo,cmd
from botocore.exceptions import ClientError
import os
import click
import shutil

def _get_aws_env_vars_or_exit():
    try:
        AWS_ACCESS_KEY = os.environ['AWS_ACCESS_KEY']
        AWS_SECRET_KEY = os.environ['AWS_SECRET_KEY']
        AWS_BUCKET_NAME = os.environ['AWS_BUCKET_NAME']
    except KeyError:
        click.echo('Environment Variables for AWS storage not found. ' +
            'Make sure AWS_ACCESS_KEY, AWS_SECRET_KEY and AWS_BUCKET_NAME are set. ' +
            'Exiting...', err=True)
        exit(1)
    return (AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_BUCKET_NAME)

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
        click.echo('Method not implemented')
        raise (NotImplementedError)

def download_archives(options, env, method):
    if method == 's3':
        download_archives_aws(options, env)
    else:
        click.echo('Method not implemented')
        raise (NotImplementedError)

def upload_archives_aws(options, env):
    (access_key, secret_key, bucket_name) = _get_aws_env_vars_or_exit()

    data_path = env['data_dir']

    postgres_archive_path = data_path / 'postgres.zip'
    solr_archive_path = data_path / 'solr.zip'
    mine_archive_path = data_path / 'biotestmine.zip'

    version = generate_version(options, env)

    s3 = boto3.client(
        's3',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key)
    bucket = bucket_name
    try:
        s3.upload_file(str(postgres_archive_path), bucket, str(version+'postgres.zip'))
        s3.upload_file(str(solr_archive_path), bucket, str(version+'solr.zip'))
        s3.upload_file(str(mine_archive_path), bucket, str(version+'biotestmine.zip'))
    except ClientError as error:
        click.echo(error, err=True)

def download_archives_aws(options, env):
    (access_key, secret_key, bucket_name) = _get_aws_env_vars_or_exit()

    data_path = env['data_dir']
    data_dir = data_path / 'data'

    postgres_data_dir = data_dir / 'postgres'
    solr_data_dir = data_dir / 'solr'
    mine_data_dir = data_dir / 'mine'

    version = generate_version(options, env)

    # download the archives
    s3 = boto3.client(
        's3',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key)
    bucket = bucket_name
    try:
        s3.download_file(bucket, str(version+'postgres.zip'), str(data_dir / 'postgres.zip'))
        s3.download_file(bucket, str(version+'solr.zip'), str(data_dir / 'solr.zip'))
        s3.download_file(bucket, str(version+'biotestmine.zip'), str(data_dir / 'mine.zip'))
    except ClientError as error:
        click.echo(error, err=True)

    # unzip
    shutil.unpack_archive(str(data_dir / 'postgres.zip'), str(postgres_data_dir), 'zip')
    shutil.unpack_archive(str(data_dir / 'solr.zip'), str(solr_data_dir), 'zip')
    shutil.unpack_archive(str(data_dir / 'mine.zip'), str(mine_data_dir), 'zip')

    # delete the zips
    os.remove(str(data_dir / 'postgres.zip'))
    os.remove(str(data_dir / 'solr.zip'))
    os.remove(str(data_dir / 'mine.zip'))
