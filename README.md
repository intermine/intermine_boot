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
$ virtualenv venv
$ . venv/bin/activate
$ pip install --editable .
# Change the source code and call intermine_boot however you want.
$ intermine_boot
# Exit virtualenv when done.
$ deactivate
```

## TODO

- The amount of conditionals is making it very difficult to determine the codepath of each mode. We should decompose the code into smaller functions describing what they do, then define code paths clearly by calling these. It will be less DRY, but hopefully much more readable.
- Find a way to merge the two different `docker-compose.yaml` files. If this really isn't practical to do, we need to persist which compose file is used, so it later can be targetted for `stop` mode.
- Update intermine_builder to handle an already built mine (ie. just deploy to tomcat)
    - Also make it handle building InterMine
