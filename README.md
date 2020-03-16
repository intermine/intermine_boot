# intermine_boot

A little app to spin up local containers in which to build an InterMine

## Description

An InterMine, commonly referred to as an InterMine instance or simply a mine, is one of many biological data warehouses based on the InterMine open source software. They provide a webapp and a webservice that multiple InterMine clients in different programming languages (eg. Python and JavaScript) can query to receive integrated biological data.

Building and running an InterMine is an arduous process which requires Linux system adminstration skills, and provisioned servers if you want your InterMine to be publicly available. InterMine Cloud attempts to solve this and lower the barrier to building and running an InterMine instance.

This tool is one part of InterMine Cloud, focused on providing its features in a local environment.

## Features

*Note: This tool is under development and the listed features are only the ones currently implemented (more are planned!).*

- Starting and stopping a complete biotestmine (`intermine_boot start local` and `intermine_boot stop local`)
- Use a custom build of InterMine with flags `--build-im`, `--im-repo` and `--im-branch`

## Requirements
- Python 3.5+
- Git
- docker
- [docker-compose](https://docs.docker.com/compose/install/)

## Development

Install [virtualenv](https://virtualenv.pypa.io/en/stable/installation/) if you haven't already.

```bash
$ virtualenv -p python3 venv
$ . venv/bin/activate
$ pip install --editable .
# Change the source code and call intermine_boot however you want.
$ intermine_boot
# Exit virtualenv when done.
$ deactivate
```
