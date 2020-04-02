import boto3
#from botocore.exceptions import ClientError

def upload(options, env):
    postgres_file = _get_compose_path(options, env).parent / 'data' /'postgres' / env['data_dir'] / 'postgres.tar.xz'
    biotestmine_file = _get_compose_path(options, env).parent / 'data' /'biotestmine' / env['data_dir'] / 'biotestmine.tar.xz'
    solr_file = _get_compose_path(options, env).parent / 'data' /'solr' / env['data_dir'] / 'solr.tar.xz'
   
    s3 = boto3.client('s3', aws_access_key_id=aws_access_key_id, aws_secret_acess_key=aws_access_key_id)

    s3 = boto3.resource('s3')
    obj = s3.create_bucket(Bucket= 'Intermine').object('data_archive')
    # Metadata to add
    metadata = {"version" => "1.0"}

    obj.upload_file(biotestmine_file, metadata: metadata)
    obj.upload_file(solr_file, metadata: metadata)
    obj.upload_file(postgres_file, metadata: metadata)

