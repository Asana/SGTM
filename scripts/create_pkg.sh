#! /bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

# Instructions taken from
# https://alek-cora-glez.medium.com/deploying-aws-lambda-function-with-terraform-custom-dependencies-7874407cd4fc

echo "Executing create_pkg.sh..."

echo "Source code path is set to $source_code_path"
cd $path_cwd
# PIPENV_PIPFILE=$path_cwd/Pipfile
dist_dir_name=lambda_dist_pkg/
echo "$PIPENV_PIPFILE"

echo "Creating directory $dist_dir_name within $path_cwd..."
mkdir -p $dist_dir_name

# Create and activate virtual environment, and install python dependencies...
# echo "Creating and activating virtual environment..."
pipenv install

# Create deployment package...
echo "Creating deployment package..."

# install dependencies into a temporary directory other than $dist_dir_name
mkdir -p tmp
pipenv run pip install -r <(pipenv requirements) --platform manylinux2014_x86_64 --only-binary=:all: --target tmp

# Copy source code to the deployment package directory
cp -R "$path_cwd"/"$source_code_path" "$path_cwd"/$dist_dir_name
# Copy the dependencies to the deployment package directory
cp -R tmp/* "$path_cwd"/$dist_dir_name

# Remove the temporary directory
rm -rf tmp

echo "Finished script execution!"
