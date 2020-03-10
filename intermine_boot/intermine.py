"""
This file is not currently in use, as the building of InterMine has been moved
into the intermine:builder docker container.
https://github.com/intermine/docker-intermine-gradle
If this changes, update this docstring.
"""
import tempfile
from pathlib import Path
import subprocess
import re
import sys
import click
from git import Repo
from intermine_boot import utils

IM_INSTALL_DIRS = [['plugin'], ['intermine'], ['bio'],
                   ['bio', 'sources'], ['bio', 'postprocess']]

IM_VERSION_PATH = ['intermine', 'build.gradle']
BIO_VERSION_PATH = ['bio', 'build.gradle']


def read_version_string(file_path):
    with open(file_path) as file:
        for line in file:
            match = re.findall(r'version[\s=]+\'(.*)\'', line)
            if match:
                return match[0]

    click.echo('Failed to read version string from ' + file_path, err=True)
    click.echo("It's likely the source files have changed and intermine_boot needs to be updated to work again.", err=True)
    sys.exit(1)


def main(**options):
    with tempfile.TemporaryDirectory(prefix='intermine_boot_') as tmpdir:
        tmpdir = Path(tmpdir)

        click.echo('Cloning GitHub repository for building InterMine')

        im_repo_dir = tmpdir / 'intermine'

        Repo.clone_from(options['im_repo'], im_repo_dir,
                        progress=utils.GitProgressPrinter(),
                        multi_options=['--single-branch',
                                       '--branch ' + options['im_branch']])

        click.echo('Will build ' + options['im_branch'] + ' branch of ' + options['im_repo'])

        with click.progressbar(length=len(IM_INSTALL_DIRS)*2,
                               show_eta=False,
                               label='Building InterMine:') as im_progress:

            im_progress.update(0)

            for install_dir in IM_INSTALL_DIRS:

                subprocess.run(['./gradlew', 'clean'],
                               check=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               cwd=im_repo_dir.joinpath(*install_dir))
                im_progress.update(1)
                subprocess.run(['./gradlew', 'install'],
                               check=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               cwd=im_repo_dir.joinpath(*install_dir))
                im_progress.update(1)

        im_build_file = im_repo_dir.joinpath(*IM_VERSION_PATH)
        bio_build_file = im_repo_dir.joinpath(*BIO_VERSION_PATH)

        return {
            'im_version': read_version_string(im_build_file),
            'bio_version': read_version_string(bio_build_file)
        }
