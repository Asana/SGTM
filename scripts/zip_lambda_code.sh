#! /bin/bash
set -e

python3 -m venv v-env
source v-env/bin/activate

pip3 install -r requirements.txt

cd v-env/lib/python3.7/site-packages

zip -r9 ${OLDPWD}/build/function.zip .

cd $OLDPWD

zip build/function.zip -r src/*
