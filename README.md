# intermine_boot

A little app to spin up local containers in which to build an InterMine

## Development

**Requires:**
- [virtualenv](https://virtualenv.pypa.io/en/stable/installation/)
- Python 3

```bash
$ virtualenv venv
$ . venv/bin/activate
$ pip install --editable .
# Change the source code and call intermine_boot however you want.
$ intermine_boot
# Exit virtualenv when done.
$ deactivate
```
