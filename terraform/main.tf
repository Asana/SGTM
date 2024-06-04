provider "aws" {
  region = var.aws_region
}



import {
  to = module.sgtm-prod.aws_cloudwatch_log_group.main
  id = "/aws/lambda/sgtm"
}


import {
  to = module.sgtm-prod.aws_s3_object.lambda_code_bundle
  id = "${var.lambda_code_s3_bucket_name}/sgtm_bundle.zip"
}


moved {
  from = module.sgtm-prod.aws_iam_role.iam_for_lambda_function
  to   = module.sgtm-prod.aws_iam_role.sgtm_lambda
}


moved {
  from = module.sgtm-staging.aws_iam_role.iam_for_lambda_function
  to   = module.sgtm-staging.aws_iam_role.sgtm_lambda
}

import {
  to = module.sgtm-staging.aws_cloudwatch_log_group.main
  id = "/aws/lambda/sgtm_staging"
}

import {
  to = module.sgtm-staging.aws_s3_object.lambda_code_bundle
  id = "${var.lambda_code_s3_bucket_name}/sgtm_bundle_staging.zip"
}



module "sgtm-prod" {
  source = "./sgtm-cluster"

  # API keys retrieval
  api_encryption_key_arn    = aws_kms_key.api_encryption_key.arn
  api_key_s3_bucket_name    = var.api_key_s3_bucket_name
  api_key_s3_object         = var.api_key_s3_object
  s3_api_key_bucket_arn     = aws_s3_bucket.api_key_bucket.arn
  custom_config_bucket_name = var.custom_config_bucket_name

  # DynamoDB configuration
  aws_region                = var.aws_region
  dynamodb-sgtm-lock-arn    = aws_dynamodb_table.sgtm-lock.arn
  dynamodb-sgtm-objects-arn = aws_dynamodb_table.sgtm-objects.arn

  # Github usernames to Asana GIDs mapping
  github_usernames_to_asana_gids_s3_path = var.github_usernames_to_asana_gids_s3_path

  # Lambda function configuration
  lambda_code_s3_bucket_name = var.lambda_code_s3_bucket_name
  lambda_function_timeout    = var.lambda_function_timeout
  lambda_runtime             = var.lambda_runtime

  # SGTM feature flags
  sgtm_feature__allow_persistent_task_assignee   = var.sgtm_feature__allow_persistent_task_assignee
  sgtm_feature__autocomplete_enabled             = var.sgtm_feature__autocomplete_enabled
  sgtm_feature__automerge_enabled                = var.sgtm_feature__automerge_enabled
  sgtm_feature__check_rerun_base_ref_names       = var.sgtm_feature__check_rerun_base_ref_names
  sgtm_feature__check_rerun_on_approval_enabled  = var.sgtm_feature__check_rerun_on_approval_enabled
  sgtm_feature__check_rerun_threshold_hours      = var.sgtm_feature__check_rerun_threshold_hours
  sgtm_feature__disable_github_team_subscription = var.sgtm_feature__disable_github_team_subscription
  sgtm_feature__followup_review_github_users     = var.sgtm_feature__followup_review_github_users

  # API Gateway configuration
  sgtm_rest_api_id               = aws_api_gateway_rest_api.sgtm_rest_api.id
  sgtm_rest_api_root_resource_id = aws_api_gateway_rest_api.sgtm_rest_api.root_resource_id
  sgtm_rest_api_execution_arn    = aws_api_gateway_rest_api.sgtm_rest_api.execution_arn

  # github authentication configuration
  github_app_name                                    = var.github_app_name
  custom_lambda_role_policy_s3_object_key            = var.custom_lambda_role_policy_s3_object_key
  github_app_installation_access_token_retrieval_url = var.github_app_installation_access_token_retrieval_url
}


module "sgtm-staging" {
  source                = "./sgtm-cluster"
  naming_cluster_suffix = "staging"

  # API keys retrieval
  api_encryption_key_arn    = aws_kms_key.api_encryption_key.arn
  api_key_s3_bucket_name    = var.api_key_s3_bucket_name
  api_key_s3_object         = var.api_key_s3_object
  s3_api_key_bucket_arn     = aws_s3_bucket.api_key_bucket.arn
  custom_config_bucket_name = var.custom_config_bucket_name

  # DynamoDB configuration
  aws_region                = var.aws_region
  dynamodb-sgtm-lock-arn    = aws_dynamodb_table.sgtm-lock.arn
  dynamodb-sgtm-objects-arn = aws_dynamodb_table.sgtm-objects.arn

  # Github usernames to Asana GIDs mapping
  github_usernames_to_asana_gids_s3_path = var.github_usernames_to_asana_gids_s3_path

  # Lambda function configuration
  lambda_code_s3_bucket_name = var.lambda_code_s3_bucket_name
  lambda_function_timeout    = var.lambda_function_timeout
  lambda_runtime             = var.lambda_runtime

  # SGTM feature flags
  sgtm_feature__allow_persistent_task_assignee   = var.sgtm_feature__allow_persistent_task_assignee
  sgtm_feature__autocomplete_enabled             = var.sgtm_feature__autocomplete_enabled
  sgtm_feature__automerge_enabled                = var.sgtm_feature__automerge_enabled
  sgtm_feature__check_rerun_base_ref_names       = var.sgtm_feature__check_rerun_base_ref_names
  sgtm_feature__check_rerun_on_approval_enabled  = var.sgtm_feature__check_rerun_on_approval_enabled
  sgtm_feature__check_rerun_threshold_hours      = var.sgtm_feature__check_rerun_threshold_hours
  sgtm_feature__disable_github_team_subscription = var.sgtm_feature__disable_github_team_subscription
  sgtm_feature__followup_review_github_users     = var.sgtm_feature__followup_review_github_users

  # API Gateway configuration
  sgtm_rest_api_id               = aws_api_gateway_rest_api.sgtm_rest_api.id
  sgtm_rest_api_root_resource_id = aws_api_gateway_rest_api.sgtm_rest_api.root_resource_id
  sgtm_rest_api_execution_arn    = aws_api_gateway_rest_api.sgtm_rest_api.execution_arn

  # github authentication configuration
  github_app_name                                    = var.github_app_name
  custom_lambda_role_policy_s3_object_key            = var.custom_lambda_role_policy_s3_object_key
  github_app_installation_access_token_retrieval_url = var.github_app_installation_access_token_retrieval_url
}

resource "aws_s3_bucket" "lambda_code_s3_bucket" {
  bucket = var.lambda_code_s3_bucket_name
}

### API

resource "aws_api_gateway_rest_api" "sgtm_rest_api" {
  name        = "SgtmRestApi"
  description = "The API gateway for SGTM lambda function"
  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

### DYNAMODB
# ##DynamoDbSchema The DynamoDbSchema's source of truth is to be found here, in the sgtm/terraform/main.tf, except for
# the sgtm_terraform_state_lock table, which has it's source of truth in scripts/setup.py

resource "aws_dynamodb_table" "sgtm-lock" {
  name           = "sgtm-lock"
  read_capacity  = 15
  write_capacity = 15
  hash_key       = "lock_key"
  range_key      = "sort_key"

  attribute {
    name = "lock_key"
    type = "S"
  }

  attribute {
    name = "sort_key"
    type = "S"
  }

  ttl {
    attribute_name = "expiry_time"
    enabled        = true
  }
}

resource "aws_dynamodb_table" "sgtm-objects" {
  name           = "sgtm-objects"
  read_capacity  = 5
  write_capacity = 5
  hash_key       = "github-node"

  attribute {
    name = "github-node"
    type = "S"
  }

  # Since this is a table that contains important data that we can't recover,
  # adding prevent_destroy saves us from accidental updates that would destroy
  # this resource
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_kms_key" "api_encryption_key" {
  description             = "This key is used to encrypt api key bucket objects"
  deletion_window_in_days = 10
}

# This is a temporary fix for the breaking changes made to the "aws_s3_bucket" resource in v4.0 of the Terraform AWS Provider
# This fix is from one of the issues raised regarding the breaking change. https://github.com/hashicorp/terraform-provider-aws/issues/23125#issuecomment-1036412659
# Ongoing discussion regarding the breaking change has been moved to this issue. https://github.com/hashicorp/terraform-provider-aws/issues/23106
terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
      # The lowest version that supports the aws_s3_object attribute.
      version = ">= 4.0"
    }
  }
}

resource "aws_s3_bucket" "api_key_bucket" {
  bucket = var.api_key_s3_bucket_name

  # See: https://github.com/hashicorp/terraform-provider-aws/issues/23106#issuecomment-1099401600
  lifecycle {
    ignore_changes = [
      server_side_encryption_configuration
    ]
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "api_key_bucket_server_side_encryption_configuration" {
  bucket = aws_s3_bucket.api_key_bucket.bucket
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.api_encryption_key.arn
      sse_algorithm     = "aws:kms"
    }
  }
}
