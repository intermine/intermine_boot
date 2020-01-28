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
