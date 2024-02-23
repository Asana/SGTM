# Should be able to use vars directly in main.tf, but can't
# in backend configuration, so we use terragrunt for now.
# See: https://github.com/hashicorp/terraform/issues/13022
generate "backend" {
  path = "backend.tf"
  if_exists = "overwrite_terragrunt"
  contents = <<EOF
terraform {
  backend "remote" {
    organization = "asana"
    workspaces {
      name = "sgtm"
    }
  }
}
EOF
}
