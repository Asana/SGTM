# Should be able to use vars directly in main.tf, but can't
# in backend configuration, so we use terragrunt for now.
# See: https://github.com/hashicorp/terraform/issues/13022
remote_state {
  backend = "s3"
  generate = {
    path      = "backend.tf"
    if_exists = "overwrite_terragrunt"
  }
  config = {
    bucket = "${get_env("terraform_backend_s3_bucket_name")}"
    dynamodb_table = "sgtm_terraform_state_lock"
    region = "us-east-1"

    key = "${path_relative_to_include()}/terraform.tfstate"
    # encrypt        = true
  }
}
