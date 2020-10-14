remote_state {
  backend = "s3"
  generate = {
    path      = "backend.tf"
    if_exists = "overwrite_terragrunt"
  }
  config = {
    bucket = "${get_env("terraform_backend_s3_bucket_name")}"#var.terraform_backend_s3_bucket_name
    dynamodb_table = "sgtm_terraform_state_lock" # var.terraform_backend_dynamodb_lock_table
    region = "us-east-1" # var.aws_region

    key = "${path_relative_to_include()}/terraform.tfstate"
    # encrypt        = true

  }
}
