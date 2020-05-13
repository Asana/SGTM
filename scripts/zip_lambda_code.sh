#! /bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

# Instructions taken from
# https://docs.aws.amazon.com/lambda/latest/dg/lambda-python-how-to-create-deployment-package.html#python-package-venv

# Create a virtualenvironment and activate
python3 -m venv build-env
source build-env/bin/activate

# Install the production Python requirements
pip3 install -r requirements.txt

# Zip the dependencies into the output archive
cd build-env/lib/python3.7/site-packages
rm -f ${OLDPWD}/build/function.zip
zip -r9 ${OLDPWD}/build/function.zip .

# Zip the source code into the output archive
cd $OLDPWD
mkdir -p build
zip build/function.zip -r src/*
