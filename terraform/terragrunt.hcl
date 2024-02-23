# Should be able to use vars directly in main.tf, but can't
# in backend configuration, so we use terragrunt for now.
# See: https://github.com/hashicorp/terraform/issues/13022
generate "backend" {
  path = "backend.tf"
  if_exists = "overwrite_terragrunt"
  contents = <<EOF
terraform {
%{ if get_env("TF_VAR_terraform_backend_use_tfc", false) }
  backend "remote" {
    organization = "${get_env("TF_VAR_terraform_backend_organization_name")}"
    workspaces {
      name = "${get_env("TF_VAR_terraform_backend_workspace_name")}"
    }
  }
%{ else }
  backend "s3" {
    bucket = "${get_env("TF_VAR_terraform_backend_s3_bucket_name")}"
    dynamodb_table = "sgtm_terraform_state_lock"
    region = "us-east-1"

    key = "${path_relative_to_include()}/terraform.tfstate"
  }
%{ endif }
}
EOF
}
