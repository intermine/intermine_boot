# intermine_boot

A little app to spin up local containers in which to build an InterMine

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

## TODO

- Find a way to merge the two different `docker-compose.yaml` files. If this really isn't practical to do, we need to persist which compose file is used, so it later can be targetted for `stop` mode.
- Convert usage of docker-compose to using docker python library directly
- Update intermine_builder to handle an already built mine (ie. just deploy to tomcat)
- Create archive for InterMine as well (when a custom one has been built)
