# SGTM
One-way sync of GitHub pull requests to Asana tasks so engineers can track all of their work in Asana.

This is an adapted version of a Clojure app that was originally written for internal use by Asana engineers and is still under active development.

## Installation
We recommend setting up a virtualenvironment to install and run your python environment. By doing so, you can eliminate
the risk that SGTM's python dependencies and settings will be mixed up with any such dependencies and settings that you
may be using in other projects.

When first setting up your repository, we recommend using a virtual environment. Once you have that activated (see below), you should install all required python dependencies using `pip3 install -r requirements.txt -r requirements-dev.txt`.

### Installing a Virtual Environment for Python

See [these instructions](https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/) for help in
setting up a virtual environment for Python, or use the following TL;DR version:

* run `python3 -m venv v-env` to create a virtual environment
* run `source v-env/bin/activate` to activate and enter your virtual environment
* once activated, run `deactivate` to deactivate and leave your virtual environment

## Running Tests

To run the tests, you must set the AWS_DEFAULT_REGION environment variable. This is required because some of the tests
are integration tests that require DynamoDb. This needs to be exported, so that it is available to sub-processes. Here's how:
```bash
if [ -z "$AWS_DEFAULT_REGION" ]; then export AWS_DEFAULT_REGION="us-east-1"; else export AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION; fi
```

You may then run all tests via the command line:

```bash
python3 -m unittest discover
```

Alternatively, you may run specific tests e.g. via:

```bash
python3 ./test/<python-test-file-name>.py>
python3 ./test/<python-test-file-name>.py> <TestClassName>
python3 ./test/<python-test-file-name>.py> <TestClassName.test_function_name>
```

## "Building"

Please perform the following checks prior to pushing code

* run `black .` to autoformat your code
* run `mypy` on each file that you have changed
* run tests, as described in the previous section

