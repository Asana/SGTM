provider "aws" {
  region = var.aws_region
}

module "sgtm-prod" {
  source                                         = "./sgtm-cluster"
  api_encryption_key_arn                         = aws_kms_key.api_encryption_key.arn
  api_key_s3_bucket_name                         = var.api_key_s3_bucket_name
  api_key_s3_object                              = var.api_key_s3_object
  dynamodb-sgtm-lock-arn                         = aws_dynamodb_table.sgtm-lock.arn
  dynamodb-sgtm-objects-arn                      = aws_dynamodb_table.sgtm-objects.arn
  github_usernames_to_asana_gids_s3_path         = var.github_usernames_to_asana_gids_s3_path
  lambda_code_s3_bucket_name                     = var.lambda_code_s3_bucket_name
  lambda_function_timeout                        = var.lambda_function_timeout
  lambda_runtime                                 = var.lambda_runtime
  s3_api_key_bucket_arn                          = aws_s3_bucket.api_key_bucket.arn
  sgtm_feature__allow_persistent_task_assignee   = var.sgtm_feature__allow_persistent_task_assignee
  sgtm_feature__autocomplete_enabled             = var.sgtm_feature__autocomplete_enabled
  sgtm_feature__automerge_enabled                = var.sgtm_feature__automerge_enabled
  sgtm_feature__check_rerun_base_ref_names       = var.sgtm_feature__check_rerun_base_ref_names
  sgtm_feature__check_rerun_on_approval_enabled  = var.sgtm_feature__check_rerun_on_approval_enabled
  sgtm_feature__check_rerun_threshold_hours      = var.sgtm_feature__check_rerun_threshold_hours
  sgtm_feature__disable_github_team_subscription = var.sgtm_feature__disable_github_team_subscription
  sgtm_feature__followup_review_github_users     = var.sgtm_feature__followup_review_github_users
  sgtm_rest_api_id                               = aws_api_gateway_rest_api.sgtm_rest_api.id
  sgtm_rest_api_root_resource_id                 = aws_api_gateway_rest_api.sgtm_rest_api.root_resource_id
  sgtm_rest_api_execution_arn                    = aws_api_gateway_rest_api.sgtm_rest_api.execution_arn
}


module "sgtm-staging" {
  source                                         = "./sgtm-cluster"
  naming_suffix                                  = "staging"
  api_encryption_key_arn                         = aws_kms_key.api_encryption_key.arn
  api_key_s3_bucket_name                         = var.api_key_s3_bucket_name
  api_key_s3_object                              = var.api_key_s3_object
  dynamodb-sgtm-lock-arn                         = aws_dynamodb_table.sgtm-lock.arn
  dynamodb-sgtm-objects-arn                      = aws_dynamodb_table.sgtm-objects.arn
  github_usernames_to_asana_gids_s3_path         = var.github_usernames_to_asana_gids_s3_path
  lambda_code_s3_bucket_name                     = var.lambda_code_s3_bucket_name
  lambda_function_timeout                        = var.lambda_function_timeout
  lambda_runtime                                 = var.lambda_runtime
  s3_api_key_bucket_arn                          = aws_s3_bucket.api_key_bucket.arn
  sgtm_feature__allow_persistent_task_assignee   = var.sgtm_feature__allow_persistent_task_assignee
  sgtm_feature__autocomplete_enabled             = var.sgtm_feature__autocomplete_enabled
  sgtm_feature__automerge_enabled                = var.sgtm_feature__automerge_enabled
  sgtm_feature__check_rerun_base_ref_names       = var.sgtm_feature__check_rerun_base_ref_names
  sgtm_feature__check_rerun_on_approval_enabled  = var.sgtm_feature__check_rerun_on_approval_enabled
  sgtm_feature__check_rerun_threshold_hours      = var.sgtm_feature__check_rerun_threshold_hours
  sgtm_feature__disable_github_team_subscription = var.sgtm_feature__disable_github_team_subscription
  sgtm_feature__followup_review_github_users     = var.sgtm_feature__followup_review_github_users
  sgtm_rest_api_id                               = aws_api_gateway_rest_api.sgtm_rest_api.id
  sgtm_rest_api_root_resource_id                 = aws_api_gateway_rest_api.sgtm_rest_api.root_resource_id
  sgtm_rest_api_execution_arn                    = aws_api_gateway_rest_api.sgtm_rest_api.execution_arn
}

resource "aws_s3_bucket" "lambda_code_s3_bucket" {
  bucket = var.lambda_code_s3_bucket_name
}

resource "aws_s3_bucket_object" "lambda_code_bundle" {
  depends_on  = [null_resource.install_python_dependencies]
  bucket      = aws_s3_bucket.lambda_code_s3_bucket.bucket
  key         = "sgtm_bundle.zip"
  source      = data.archive_file.create_dist_pkg.output_path
  source_hash = data.archive_file.create_dist_pkg.output_base64sha256
}

resource "aws_lambda_function" "sgtm" {
  s3_bucket        = aws_s3_bucket.lambda_code_s3_bucket.bucket
  s3_key           = aws_s3_bucket_object.lambda_code_bundle.key
  function_name    = "sgtm"
  role             = aws_iam_role.iam_for_lambda_function.arn
  handler          = "src.handler.handler"
  source_code_hash = data.archive_file.create_dist_pkg.output_base64sha256

  runtime = var.lambda_runtime

  timeout = var.lambda_function_timeout
  environment {
    variables = {
      API_KEYS_S3_BUCKET                             = var.api_key_s3_bucket_name,
      API_KEYS_S3_KEY                                = var.api_key_s3_object,
      SGTM_FEATURE__AUTOMERGE_ENABLED                = var.sgtm_feature__automerge_enabled,
      SGTM_FEATURE__AUTOCOMPLETE_ENABLED             = var.sgtm_feature__autocomplete_enabled,
      SGTM_FEATURE__DISABLE_GITHUB_TEAM_SUBSCRIPTION = var.sgtm_feature__disable_github_team_subscription,
      SGTM_FEATURE__ALLOW_PERSISTENT_TASK_ASSIGNEE   = var.sgtm_feature__allow_persistent_task_assignee,
      SGTM_FEATURE__FOLLOWUP_REVIEW_GITHUB_USERS     = var.sgtm_feature__followup_review_github_users,
      SGTM_FEATURE__CHECK_RERUN_THRESHOLD_HOURS      = var.sgtm_feature__check_rerun_threshold_hours,
      SGTM_FEATURE__CHECK_RERUN_BASE_REF_NAMES       = var.sgtm_feature__check_rerun_base_ref_names,
      SGTM_FEATURE__CHECK_RERUN_ON_APPROVAL_ENABLED  = var.sgtm_feature__check_rerun_on_approval_enabled
    }
  }
}

resource "aws_lambda_function" "sgtm_sync_users" {
  s3_bucket        = aws_s3_bucket.lambda_code_s3_bucket.bucket
  s3_key           = aws_s3_bucket_object.lambda_code_bundle.key
  function_name    = "sgtm_sync_users"
  role             = aws_iam_role.iam_for_lambda_function.arn
  handler          = "src.sync_users.handler.handler"
  source_code_hash = data.archive_file.create_dist_pkg.output_base64sha256

  runtime = var.lambda_runtime

  timeout = 900
  environment {
    variables = {
      API_KEYS_S3_BUCKET     = var.api_key_s3_bucket_name,
      API_KEYS_S3_KEY        = var.api_key_s3_object
      ASANA_USERS_PROJECT_ID = var.asana_users_project_id
    }
  }
}

resource "aws_cloudwatch_event_rule" "execute_sgtm_sync_users_event_rule" {
  name                = "execute_sgtm_sync_users"
  description         = "Execute Lambda function sgtm_sync_users on a cron-style schedule"
  schedule_expression = "rate(1 hour)"
}

resource "aws_lambda_permission" "lambda_permission_for_sgtm_sync_users_schedule_event" {
  statement_id  = "AllowSGTMSyncUsersInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sgtm_sync_users.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.execute_sgtm_sync_users_event_rule.arn
}

resource "aws_cloudwatch_event_target" "execute_sgtm_sync_users_event_target" {
  target_id = "execute_sgtm_sync_users_event_target"
  rule      = aws_cloudwatch_event_rule.execute_sgtm_sync_users_event_rule.name
  arn       = aws_lambda_function.sgtm_sync_users.arn
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
    aws = "~> 3.27"
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
