# SGTM

## Installation
We recommend setting up a virtualenvironment to install and run your python environment.

When first setting up your repository, you should install all required python dependencies using `pip3 install -r requirements.txt -r requirements-dev.txt`.

## Running Tests

Select an AWS_DEFAULT_REGIION, if you do not have one already, e.g. via:
```bash
if [ -z "$AWS_DEFAULT_REGION" ]; then AWS_DEFAULT_REGION=us-east-1; fi;
```

Run the following via the command line:

```bash
python3 -m unittest discover
```

## Installing a Virtual Environment for Python

See [these instructions](https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/) for help in
setting up a virtual environment for Python.

* python3 -m venv sgtm
* source sgtm/bin/activate
* deactivate