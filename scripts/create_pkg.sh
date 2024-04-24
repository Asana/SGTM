#! /bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

# Instructions taken from
# https://alek-cora-glez.medium.com/deploying-aws-lambda-function-with-terraform-custom-dependencies-7874407cd4fc

echo "Executing create_pkg.sh..."

echo "Source code path is set to $source_code_path"
cd $path_cwd
dist_dir_name=lambda_dist_pkg/

echo "Creating directory $dist_dir_name within $path_cwd..."
mkdir -p $dist_dir_name

# Create and activate virtual environment, and install python dependencies...
# echo "Creating and activating virtual environment..."
pipenv install

# Activate virtual environment. This is the equivalent of prefixing all the below commands with
# `pipenv run`
pipenv shell

# Create deployment package...
echo "Creating deployment package..."

# Install dependencies to the deployment package directory
pip install -r <(pipenv lock -r) --target $dist_dir_name
pip freeze | grep cryptography
if [ $? -ne 0 ]; then
  echo "cryptography isn't installed; will skip retrieving linux version of cryptography"
else
  echo "cryptography is installed; will retrieve linux version of cryptography"
  # Install cryptography package for manylinux2014_x86_64 to the package directory
  pip install --platform manylinux2014_x86_64 --implementation cp --only-binary=:all: --upgrade --target $dist_dir_name cryptography
fi

# Copy source code to the deployment package directory
cp -R "$path_cwd"/"$source_code_path" "$path_cwd"/$dist_dir_name

# Deactivate virtual environment...
deactivate
echo "Finished script execution!"
