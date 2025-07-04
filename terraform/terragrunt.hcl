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
    %{ if get_env("TF_VAR_terraform_backend_s3_use_dynamodb_for_locks", true) }
    dynamodb_table = "sgtm_terraform_state_lock"
    %{ endif }
    %{ if get_env("TF_VAR_terraform_backend_s3_use_s3_for_locks", false) }
    use_lockfile = true
    %{ endif }
    region = "us-east-1"

    key = "${get_env("TF_VAR_terraform_backend_s3_key_prefix", path_relative_to_include())}/terraform.tfstate"
  }
%{ endif }
}
EOF
}
