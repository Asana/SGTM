variable "aws_region" {
  type        = string
  description = "The AWS region to create resources in"
  default     = "us-east-1"
}

variable "dynamodb-sgtm-lock-arn" {
  description = "The ARN of the DynamoDB table to store SGTM locks"
  type        = string
}

variable "dynamodb-sgtm-objects-arn" {
  description = "The ARN of the DynamoDB table to store SGTM objects"
  type        = string
}

variable "s3_api_key_bucket_arn" {
  description = "The ARN of the S3 bucket to store API keys"
  type        = string
}

variable "api_encryption_key_arn" {
  description = "The ARN of the KMS key to use for decrypting API keys"
  type        = string
}

variable "naming_suffix" {
  description = "A suffix to append to the names of resources"
  type        = string
  default     = null
}

variable "api_key_s3_object" {
  type        = string
  description = "Name of the API key object"
}

variable "api_key_s3_bucket_name" {
  type        = string
  description = "Name of the API key S3 bucket"
}

variable "lambda_code_s3_bucket_name" {
  type        = string
  description = "Name of the S3 bucket that stores the Lambda functions code"
}

variable "lambda_function_timeout" {
  type        = number
  description = "Timeout used for the AWS Lambda function"
  default     = 120
}

variable "lambda_runtime" {
  type        = string
  description = "Runtime of AWS Lambda function"
  default     = "python3.9"
}

variable "github_usernames_to_asana_gids_s3_path" {
  description = "The S3 path, in the form bucket/key, to the .json file that maps Github usernames to email addresses associated with Asana users."
  type        = string
}

variable "sgtm_feature__automerge_enabled" {
  type        = string
  description = "'true' if behavior to automerge pull requests with Github labels is enabled"
  default     = "false"
}

variable "sgtm_feature__autocomplete_enabled" {
  type        = string
  description = "'true' if behavior to autocomplete linked tasks with Github labels is enabled"
  default     = "false"
}

variable "sgtm_feature__disable_github_team_subscription" {
  type        = string
  description = "'true' if behavior to auto-subscribe github team members is disabled"
  default     = "false"
}

variable "sgtm_feature__allow_persistent_task_assignee" {
  type        = string
  description = "'true' if behavior to set the Asana task assignee as the PR creator with Github labels is enabled"
  default     = "false"
}

variable "sgtm_feature__followup_review_github_users" {
  type        = string
  description = "A comma-separated list of Github usernames that require follow-up review after merge"
  default     = ""
}

variable "sgtm_feature__check_rerun_threshold_hours" {
  type        = number
  description = "Number of hours after which a check run should be rerequested. Must be combined with sgtm_feature__check_rerun_base_ref_names."
  default     = 0
}

variable "sgtm_feature__check_rerun_base_ref_names" {
  type        = string
  description = "A comma-separated list of base refs that will trigger check run rerequests when stale. Must be combined with sgtm_feature__check_rerun_freshness_duration_hours."
  default     = "main,master"
}

variable "sgtm_feature__check_rerun_on_approval_enabled" {
  type        = string
  description = "'true' if a check rerun should be rerequested when a PR is approved. Must be combined with sgtm_feature__check_rerun_base_ref_names and sgtm_feature__check_rerun_threshold_hours."
  default     = "false"
}

variable "sgtm_rest_api_id" {
  type        = string
  description = "The ID of the API Gateway REST API for SGTM"
}

variable "sgtm_rest_api_root_resource_id" {
  type        = string
  description = "The ID of the root resource of the API Gateway REST API for SGTM"

}

variable "sgtm_rest_api_execution_arn" {
  type        = string
  description = "The ARN of the API Gateway execution role for SGTM"

}

locals {
  suffix = var.naming_suffix != null ? "_${var.naming_suffix}" : ""
}

provider "aws" {
  region = var.aws_region
}

### LAMBDA

resource "aws_lambda_function" "sgtm" {
  s3_bucket        = var.lambda_code_s3_bucket_name
  s3_key           = aws_s3_bucket_object.lambda_code_bundle.key
  function_name    = "sgtm${local.suffix}"
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
      GITHUB_USERNAMES_TO_ASANA_GIDS_S3_PATH         = var.github_usernames_to_asana_gids_s3_path
      SQS_URL                                        = aws_sqs_queue.sgtm-webhooks-queue-fifo.url
    }
  }
}

locals {
  dist_dir_name = "lambda_dist_pkg/pkg${local.suffix}"
}

resource "null_resource" "install_python_dependencies" {
  triggers = {
    src_sha1 = sha1(join("", [for f in fileset(path.root, "../src/**") : filesha1(f)]))
  }

  provisioner "local-exec" {
    command = "bash ${path.module}/../../scripts/create_pkg.sh"

    environment = {
      source_code_path = "../src"
      PIPENV_PIPFILE   = replace(path.cwd, "/terraform", "/Pipfile")
      function_name    = "sgtm"
      runtime          = var.lambda_runtime
      path_cwd         = path.cwd
      dist_dir_name    = local.dist_dir_name
    }
  }
}

data "archive_file" "create_dist_pkg" {
  depends_on  = [null_resource.install_python_dependencies]
  source_dir  = "${path.cwd}/${local.dist_dir_name}"
  output_path = "build/pkg${local.suffix}/function.zip"
  type        = "zip"
}

resource "aws_s3_bucket_object" "lambda_code_bundle" {
  depends_on  = [null_resource.install_python_dependencies]
  bucket      = var.lambda_code_s3_bucket_name
  key         = "sgtm_bundle${local.suffix}.zip"
  source      = data.archive_file.create_dist_pkg.output_path
  source_hash = data.archive_file.create_dist_pkg.output_base64sha256
}


# Gives the Lambda function permissions to read/write from the DynamoDb tables
resource "aws_iam_policy" "lambda-function-dynamodb-policy" {
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:Scan",
        "dynamodb:PutItem",
        "dynamodb:BatchWriteItem"
      ],
      "Resource": [
        "${var.dynamodb-sgtm-lock-arn}",
        "${var.dynamodb-sgtm-objects-arn}"
      ],
      "Effect": "Allow"
    },
    {
      "Action": [
        "dynamodb:DeleteItem",
        "dynamodb:UpdateItem"
      ],
      "Resource": [
        "${var.dynamodb-sgtm-lock-arn}"
      ],
      "Effect": "Allow"
    }
  ]
}
EOF
}

# Gives the Lambda function permissions to create cloudwatch logs
resource "aws_iam_policy" "lambda-function-cloudwatch-policy" {
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": [
        "arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/${aws_lambda_function.sgtm.function_name}:*"
      ],
      "Effect": "Allow"
    }
  ]
}
EOF
}


resource "aws_iam_role" "iam_for_lambda_function" {
  name = "iam_for_lambda${local.suffix}"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "lambda-function-dynamo-db-access-policy-attachment" {
  role       = aws_iam_role.iam_for_lambda_function.name
  policy_arn = aws_iam_policy.lambda-function-dynamodb-policy.arn
}

resource "aws_iam_role_policy_attachment" "lambda-function-cloudwatch-policy-attachment" {
  role       = aws_iam_role.iam_for_lambda_function.name
  policy_arn = aws_iam_policy.lambda-function-cloudwatch-policy.arn
}

resource "aws_iam_role_policy_attachment" "lambda-function-api-keys" {
  role       = aws_iam_role.iam_for_lambda_function.name
  policy_arn = aws_iam_policy.LambdaFunctionApiKeysBucketAccess.arn
}


resource "aws_iam_policy" "LambdaFunctionApiKeysBucketAccess" {
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion"
      ],
      "Resource": [
        "${var.s3_api_key_bucket_arn}/*"
      ],
      "Effect": "Allow"
    },
    {
      "Action": [
        "kms:Decrypt"
      ],
      "Resource": [
        "${var.api_encryption_key_arn}"
      ],
      "Effect": "Allow"
    }
  ]
}
EOF
}

# Give the lambda permission to read from the users file path at
# var.github_usernames_to_asana_gids_s3_path
resource "aws_iam_policy" "lambda-function-github-usernames-to-emails-policy" {
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion"
      ],
      "Resource": [
        "arn:aws:s3:::${var.github_usernames_to_asana_gids_s3_path}"
      ],
      "Effect": "Allow"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "lambda-function-github-usernames-to-emails-policy-attachment" {
  role       = aws_iam_role.iam_for_lambda_function.name
  policy_arn = aws_iam_policy.lambda-function-github-usernames-to-emails-policy.arn
}


# API GATEWAY
resource "aws_api_gateway_resource" "sgtm_resource" {
  rest_api_id = var.sgtm_rest_api_id
  parent_id   = var.sgtm_rest_api_root_resource_id
  path_part   = "sgtm${local.suffix}"
}

resource "aws_api_gateway_integration" "sgtm_lambda_integration" {
  rest_api_id             = var.sgtm_rest_api_id
  resource_id             = aws_api_gateway_resource.sgtm_resource.id
  http_method             = aws_api_gateway_method.sgtm_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.sgtm.invoke_arn
}

resource "aws_api_gateway_integration_response" "sgtm_proxy_response" {
  depends_on  = [aws_api_gateway_integration.sgtm_lambda_integration]
  rest_api_id = var.sgtm_rest_api_id
  resource_id = aws_api_gateway_resource.sgtm_resource.id
  http_method = aws_api_gateway_method.sgtm_post.http_method
  status_code = aws_api_gateway_method_response.proxy.status_code
}

resource "aws_api_gateway_method" "sgtm_post" {
  rest_api_id   = var.sgtm_rest_api_id
  resource_id   = aws_api_gateway_resource.sgtm_resource.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_deployment" "sgtm_deployment" {
  depends_on  = [aws_api_gateway_integration.sgtm_lambda_integration]
  rest_api_id = var.sgtm_rest_api_id
  stage_name  = "default"
}

resource "aws_api_gateway_method_response" "proxy" {
  rest_api_id = var.sgtm_rest_api_id
  resource_id = aws_api_gateway_resource.sgtm_resource.id
  http_method = aws_api_gateway_method.sgtm_post.http_method
  status_code = "200"
}

resource "aws_lambda_permission" "lambda_permission_for_sgtm_rest_api" {
  statement_id  = "AllowSGTMAPIInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sgtm.function_name
  principal     = "apigateway.amazonaws.com"

  # More: http://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-control-access-using-iam-policies-to-invoke-api.html
  source_arn = "${var.sgtm_rest_api_execution_arn}/*/${aws_api_gateway_method.sgtm_post.http_method}${aws_api_gateway_resource.sgtm_resource.path}"
}

## SQS
resource "aws_sqs_queue" "sgtm-webhooks-queue-fifo" {
  name = "sgtm-webhooks-queue${local.suffix}.fifo"
  fifo_queue = true
  content_based_deduplication = true
  visibility_timeout_seconds = 240  # 4 minutes
  message_retention_seconds = 1800  # 30 minutes
}

data "aws_iam_policy_document" "lambda_permissions_for_sqs" {
  statement {
    actions = [
      "sqs:SendMessage",
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes"
    ]
    resources = [
      aws_sqs_queue.sgtm-webhooks-queue-fifo.arn
    ]
  }
}

resource "aws_lambda_event_source_mapping" "sgtm-sqs-source" {
  event_source_arn = aws_sqs_queue.sgtm-webhooks-queue-fifo.arn
  function_name    = aws_lambda_function.sgtm.function_name
}

resource "aws_iam_policy" "lambda_permissions_for_sqs" {
  policy = data.aws_iam_policy_document.lambda_permissions_for_sqs.json
}

resource "aws_iam_role_policy_attachment" "lambda_permissions_for_sqs" {
  policy_arn = aws_iam_policy.lambda_permissions_for_sqs.arn
  role = aws_iam_role.iam_for_lambda_function.name
}

output "api_gateway_deployment_invoke_url" {
  value = "${aws_api_gateway_deployment.sgtm_deployment.invoke_url}/${aws_api_gateway_resource.sgtm_resource.path_part}"
}
