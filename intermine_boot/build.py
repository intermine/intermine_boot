from pathlib import Path
import os
import sys
import docker
import click

from intermine_builder import MineBuilder, DOCKER_NETWORK_NAME
from intermine_builder.minecompose import parse_minecompose, MineCompose

from intermine_boot.intermine_docker import create_tomcat_container, create_solr_container, create_postgres_container
from intermine_boot.utils import assert_docker


def _create_volumes(options, env, mine_name):
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
    Path(data_dir / 'mine' / mine_name).mkdir(exist_ok=True)
    Path(data_dir / 'mine' / '.intermine').mkdir(exist_ok=True)
    Path(data_dir / 'mine' / '.m2').mkdir(exist_ok=True)

    # If we unpacked from a zip archive, these files could have lost their executable bit.
    for executable in ['gradlew', 'project_build', 'setup.sh']:
        try:
            os.chmod(data_dir / 'mine' / mine_name / executable, 0o775)
        except FileNotFoundError:
            pass


def main(options, env, minecompose_path):
    mc = parse_minecompose(minecompose_path)
    # TODO log minecompose? (redacting sensitive data)

    (env['data_dir']).mkdir(parents=True, exist_ok=True)
    _create_volumes(options, env, mc.mine)

    assert_docker(options, env)
    client = docker.from_env()

    # click.echo('Pulling images...')
    # tomcat_image = client.images.pull('intermine/tomcat:latest')
    # solr_image = client.images.pull('intermine/solr:latest')
    # postgres_image = client.images.pull('intermine/postgres:latest')
    click.echo('Building images...')
    img_path = Path(__file__).parent.absolute() / 'docker-intermine-gradle'
    tomcat_image = client.images.build(
        path=str(img_path / 'tomcat'), tag='tomcat', dockerfile='tomcat.Dockerfile')[0]
    solr_image = client.images.build(
        path=str(img_path / 'solr'), tag='solr', dockerfile='solr.Dockerfile')[0]
    postgres_image = client.images.build(
        path=str(img_path / 'postgres'), tag='postgres', dockerfile='postgres.Dockerfile')[0]

    try:
        client.networks.get(DOCKER_NETWORK_NAME)
    except docker.errors.NotFound:
        client.networks.create(DOCKER_NETWORK_NAME)

    click.echo('Starting containers...')
    (tomcat_container, tomcat_status) = create_tomcat_container(client, tomcat_image, network_name=DOCKER_NETWORK_NAME)
    (solr_container, solr_status) = create_solr_container(client, solr_image, options, env, mine_name=mc.mine, network_name=DOCKER_NETWORK_NAME)
    (postgres_container, postgres_status) = create_postgres_container(client, postgres_image, options, env, mine_name=mc.mine, network_name=DOCKER_NETWORK_NAME)

    if not (tomcat_status and solr_status and postgres_status):
        click.echo('Error occurred when starting containers', err=True)
        sys.exit(1)

    click.echo('\n\nBuilding ' + mc.mine + ' within containers...\n')
    try:
        builder = MineBuilder(mc.mine, data_path=(env['data_dir'] / 'data'))
        # builder.create_properties_file(mc.properties)
        builder.clean()
        builder.build_db()

        # TODO parse project.xml and run builder.integrate() for each data source OR use builder.project_build() to test prior to this (Q: why does `postprocess` wrap each task, but `integrate` doesn't?)

        # builder.project_build()

        # TODO to support preset mine, use builder.add_data_source
        # TODO support mounting src.data.dir as volume in builder container for data sources (the user has to provide the data sources and specify the path to it; e.g. for humanmine and flymine mounting /micklem/data should be enough)

        builder.post_process()  # you sure this doesn't have to be run for each?
        builder.build_user_db()
        builder.deploy()
    except docker.errors.ContainerError as err:
        click.echo(str(err.stderr, 'utf-8'), err=True)
        return False

    return True
