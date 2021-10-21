from pathlib import Path
import os
import sys
import shutil
import time
import xml.etree.ElementTree as ET
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


def _prepare(options, env, clean_data_dir=False):
    mc = None
    if options['minecompose']:
        mc = parse_minecompose(options['minecompose'])
        # TODO log minecompose? (redacting sensitive data)
        mine_name = mc.mine
    elif options['source']:
        mine_name = Path(options['source']).name
    else:
        click.echo('You need to specify either SOURCE or --minecompose', err=True)
        sys.exit(1)

    if clean_data_dir:
        if (env['data_dir']).is_dir():
            click.echo('Removing existing data...')
            shutil.rmtree(env['data_dir'])

    (env['data_dir']).mkdir(parents=True, exist_ok=True)
    _create_volumes(options, env, mine_name)

    if clean_data_dir:
        if options['source']:
            click.echo('Source path is ' + os.path.abspath(options['source']))
            shutil.copytree(Path(options['source']),
                            (env['data_dir'] / 'data' / 'mine' / mine_name),
                            dirs_exist_ok=True)
        else:
            click.echo('No SOURCE path specified.', err=True)
            sys.exit(1)

    assert_docker(options, env)
    client = docker.from_env()

    if options['build_images']:
        click.echo('Building images...')
        img_path = Path(__file__).parent.absolute() / 'docker-intermine-gradle'
        tomcat_image = client.images.build(
            path=str(img_path / 'tomcat'), tag='tomcat', dockerfile='tomcat.Dockerfile')[0]
        solr_image = client.images.build(
            path=str(img_path / 'solr'), tag='solr', dockerfile='solr.Dockerfile')[0]
        postgres_image = client.images.build(
            path=str(img_path / 'postgres'), tag='postgres', dockerfile='postgres.Dockerfile')[0]
    else:
        click.echo('Pulling images...')
        tomcat_image = client.images.pull('intermine/tomcat:latest')
        solr_image = client.images.pull('intermine/solr:latest')
        postgres_image = client.images.pull('intermine/postgres:latest')

    try:
        client.networks.get(DOCKER_NETWORK_NAME)
    except docker.errors.NotFound:
        client.networks.create(DOCKER_NETWORK_NAME)

    click.echo('Starting containers...')
    (tomcat_container, tomcat_status) = create_tomcat_container(client, tomcat_image, network_name=DOCKER_NETWORK_NAME)
    (solr_container, solr_status) = create_solr_container(client, solr_image, options, env, mine_name=mine_name, network_name=DOCKER_NETWORK_NAME)
    (postgres_container, postgres_status) = create_postgres_container(client, postgres_image, options, env, mine_name=mine_name, network_name=DOCKER_NETWORK_NAME)

    if not (tomcat_status and solr_status and postgres_status):
        click.echo('Error occurred when starting containers', err=True)
        sys.exit(1)

    ret = { 'mine_name': mine_name }
    if mc:
        ret['mc'] = mc
    return ret


def parse_project_xml(options, env, mine_path=None, mine_name=None):
    project_xml_path = mine_path / mine_name / "project.xml"

    tree = ET.parse(project_xml_path)
    root  = tree.getroot()

    res = { 'sources': [], 'post-processing': [] }

    sources_el = root.find('sources')
    if sources_el:
        for source in sources_el.findall('source'):
            res['sources'].append(source.attrib['name'])

    postprocessing_el = root.find('post-processing')
    if postprocessing_el:
        for postprocess in postprocessing_el.findall('post-process'):
            res['post-processing'].append(postprocess.attrib['name'])

    return res


def deploy(options, env):
    prep = _prepare(options, env)
    mine_name = prep['mine_name']
    mc = prep.get('mc')

    click.echo('\n\nDeploying ' + mine_name + ' within containers...\n')
    try:
        builder = MineBuilder(mine_name, data_path=(env['data_dir'] / 'data'))
        click.echo(builder.redeploy())
    except docker.errors.ContainerError as err:
        click.echo(str(err.stderr, 'utf-8'), err=True)
        return False

    return True


def deploy_preset(options, env):
    prep = _prepare(options, env)
    mine_name = prep['mine_name']
    mc = prep.get('mc')

    click.echo('\n\nBuilding ' + mine_name + ' within containers...\n')
    try:
        builder = MineBuilder(mine_name, data_path=(env['data_dir'] / 'data'))

        # TODO to support preset mine, use builder.add_data_source

        project = parse_project_xml(options, env, mine_path=builder.mine_path, mine_name=mine_name)
        for postprocess in project['post-processing']:
            click.echo(builder.post_process(postprocess))

        click.echo(builder.build_user_db())
        click.echo(builder.deploy())
        time.sleep(60)
        click.echo(builder.redeploy())
    except docker.errors.ContainerError as err:
        click.echo(str(err.stderr, 'utf-8'), err=True)
        return False

    return True


def build(options, env):
    prep = _prepare(options, env, clean_data_dir=True)
    mine_name = prep['mine_name']
    mc = prep.get('mc')

    click.echo('\n\nBuilding ' + mine_name + ' within containers...\n')
    try:
        builder = MineBuilder(mine_name, data_path=(env['data_dir'] / 'data'), volumes=env['volumes'])
        builder.create_properties_file(mc.properties if mc else {})
        builder.clean()
        builder.build_db()

        # click.echo(builder.project_build())
        project = parse_project_xml(options, env, mine_path=builder.mine_path, mine_name=mine_name)
        for source in project['sources']:
            click.echo(builder.integrate(source))
        if not options['preset']:
            for postprocess in project['post-processing']:
                click.echo(builder.post_process(postprocess))
            click.echo(builder.build_user_db())
            click.echo(builder.deploy())
    except docker.errors.ContainerError as err:
        click.echo(str(err.stderr, 'utf-8'), err=True)
        return False

    return True


def build_and_deploy(options, env):
    prep = _prepare(options, env, clean_data_dir=True)
    mine_name = prep['mine_name']
    mc = prep.get('mc')

    click.echo('\n\nBuilding ' + mine_name + ' within containers...\n')
    try:
        builder = MineBuilder(mine_name, data_path=(env['data_dir'] / 'data'), volumes=env['volumes'])
        builder.create_properties_file(mc.properties if mc else {})
        builder.clean()
        builder.build_db()

        # click.echo(builder.project_build())
        project = parse_project_xml(options, env, mine_path=builder.mine_path, mine_name=mine_name)
        for source in project['sources']:
            click.echo(builder.integrate(source))
        for postprocess in project['post-processing']:
            click.echo(builder.post_process(postprocess))

        click.echo(builder.build_user_db())
        click.echo(builder.deploy())
        time.sleep(60)
        click.echo(builder.redeploy())
    except docker.errors.ContainerError as err:
        click.echo(str(err.stderr, 'utf-8'), err=True)
        return False

    return True
