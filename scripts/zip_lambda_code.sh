#! /bin/bash
set -e

# Instructions taken from
# https://docs.aws.amazon.com/lambda/latest/dg/lambda-python-how-to-create-deployment-package.html#python-package-venv

# Create a virtualenvironment and activate
python3 -m venv v-env
source v-env/bin/activate

# Install the production Python requirements
pip3 install -r requirements.txt

# Zip the dependencies into the output archive
cd v-env/lib/python3.7/site-packages
zip -r9 ${OLDPWD}/build/function.zip .

# Zip the source code into the output archive
cd $OLDPWD
zip build/function.zip -r src/*
