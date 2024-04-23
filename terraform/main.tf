provider "aws" {
  region = var.aws_region
}

### LAMBDA


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
        "${aws_dynamodb_table.sgtm-lock.arn}",
        "${aws_dynamodb_table.sgtm-objects.arn}",
        "${aws_dynamodb_table.sgtm-users.arn}"
      ],
      "Effect": "Allow"
    },
    {
      "Action": [
        "dynamodb:DeleteItem",
        "dynamodb:UpdateItem"
      ],
      "Resource": [
        "${aws_dynamodb_table.sgtm-lock.arn}"
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
  name = "iam_for_lambda"

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
        "${aws_s3_bucket.api_key_bucket.arn}/*"
      ],
      "Effect": "Allow"
    },
    {
      "Action": [
        "kms:Decrypt"
      ],
      "Resource": [
        "${aws_kms_key.api_encryption_key.arn}"
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

resource "null_resource" "install_python_dependencies" {
  triggers = {
    src_sha1 = sha1(join("", [for f in fileset(path.root, "../src/**") : filesha1(f)]))
  }

  provisioner "local-exec" {
    command = "bash ${path.module}/../scripts/create_pkg.sh"

    environment = {
      source_code_path = "../src"
      PIPENV_PIPFILE   = replace(path.cwd, "/terraform", "/Pipfile")
      function_name    = "sgtm"
      runtime          = var.lambda_runtime
      path_cwd         = path.cwd
    }
  }
}


data "archive_file" "create_dist_pkg" {
  depends_on  = [null_resource.install_python_dependencies]
  source_dir  = "${path.cwd}/lambda_dist_pkg/"
  output_path = "build/function.zip"
  type        = "zip"
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
      GITHUB_USERNAMES_TO_ASANA_GIDS_S3_PATH         = var.github_usernames_to_asana_gids_s3_path
    }
  }
}

resource "aws_lambda_alias" "sgtm_lambda_alias" {
  name             = "sgtm_alias"
  description      = "alias for sgtm with sqs"
  function_name    = aws_lambda_function.sgtm.arn
  function_version = aws_lambda_function.sgtm.version
}


### API

resource "aws_api_gateway_rest_api" "sgtm_rest_api" {
  name        = "SgtmRestApi"
  description = "The API gateway for SGTM lambda function"
  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

resource "aws_api_gateway_resource" "sgtm_resource" {
  rest_api_id = aws_api_gateway_rest_api.sgtm_rest_api.id
  parent_id   = aws_api_gateway_rest_api.sgtm_rest_api.root_resource_id
  path_part   = "sgtm"
}

resource "aws_api_gateway_method" "sgtm_post" {
  rest_api_id   = aws_api_gateway_rest_api.sgtm_rest_api.id
  resource_id   = aws_api_gateway_resource.sgtm_resource.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_deployment" "sgtm_deployment" {
  depends_on  = [aws_api_gateway_integration.sgtm_lambda_integration]
  rest_api_id = aws_api_gateway_rest_api.sgtm_rest_api.id
  stage_name  = "default"
}

resource "aws_api_gateway_method_response" "proxy" {
  rest_api_id = aws_api_gateway_rest_api.sgtm_rest_api.id
  resource_id = aws_api_gateway_resource.sgtm_resource.id
  http_method = aws_api_gateway_method.sgtm_post.http_method
  status_code = "200"
}

resource "aws_api_gateway_integration" "sgtm_lambda_integration" {
  rest_api_id             = aws_api_gateway_rest_api.sgtm_rest_api.id
  resource_id             = aws_api_gateway_resource.sgtm_resource.id
  http_method             = aws_api_gateway_method.sgtm_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.sgtm.invoke_arn
}

resource "aws_api_gateway_integration_response" "sgtm_proxy_response" {
  depends_on  = [aws_api_gateway_integration.sgtm_lambda_integration]
  rest_api_id = aws_api_gateway_rest_api.sgtm_rest_api.id
  resource_id = aws_api_gateway_resource.sgtm_resource.id
  http_method = aws_api_gateway_method.sgtm_post.http_method
  status_code = aws_api_gateway_method_response.proxy.status_code
}

resource "aws_lambda_permission" "lambda_permission_for_sgtm_rest_api" {
  statement_id  = "AllowSGTMAPIInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sgtm.function_name
  principal     = "apigateway.amazonaws.com"

  # More: http://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-control-access-using-iam-policies-to-invoke-api.html
  source_arn = "${aws_api_gateway_rest_api.sgtm_rest_api.execution_arn}/*/${aws_api_gateway_method.sgtm_post.http_method}${aws_api_gateway_resource.sgtm_resource.path}"
}

### API + SQS
resource "aws_api_gateway_rest_api" "sgtm_rest_api_for_sqs" {
  name        = "SgtmRestApiV2"
  description = "The API gateway for SGTM lambda function with SQS"
  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

resource "aws_api_gateway_resource" "sgtm_resource_for_sqs" {
  rest_api_id = aws_api_gateway_rest_api.sgtm_rest_api_for_sqs.id
  parent_id   = aws_api_gateway_rest_api.sgtm_rest_api_for_sqs.root_resource_id
  path_part   = "sgtm"
}

resource "aws_api_gateway_method" "sgtm_post_for_sqs" {
  rest_api_id   = aws_api_gateway_rest_api.sgtm_rest_api_for_sqs.id
  resource_id   = aws_api_gateway_resource.sgtm_resource_for_sqs.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_deployment" "sgtm_deployment_for_sqs" {
  depends_on  = [aws_api_gateway_integration.sgtm_sqs_integration]
  rest_api_id = aws_api_gateway_rest_api.sgtm_rest_api_for_sqs.id
  stage_name  = "default"
}

resource "aws_api_gateway_method_response" "proxy_for_sqs" {
  rest_api_id = aws_api_gateway_rest_api.sgtm_rest_api_for_sqs.id
  resource_id = aws_api_gateway_resource.sgtm_resource_for_sqs.id
  http_method = aws_api_gateway_method.sgtm_post_for_sqs.http_method
  status_code = "200"
}

resource "aws_api_gateway_method_settings" "sgtm_api_settings_for_sqs" {
  rest_api_id = aws_api_gateway_rest_api.sgtm_rest_api_for_sqs.id
  stage_name  = aws_api_gateway_deployment.sgtm_deployment_for_sqs.stage_name
  method_path = "*/*"
  settings {
    logging_level = "INFO"
    data_trace_enabled = true
    metrics_enabled = true
  }
}

resource "aws_api_gateway_integration" "sgtm_sqs_integration" {
  rest_api_id             = aws_api_gateway_rest_api.sgtm_rest_api_for_sqs.id
  resource_id             = aws_api_gateway_resource.sgtm_resource_for_sqs.id
  http_method             = aws_api_gateway_method.sgtm_post_for_sqs.http_method
  integration_http_method = "POST"
  type                    = "AWS"
  passthrough_behavior    = "NEVER"
  credentials             = "${aws_iam_role.iam_for_api_gateway.arn}"
  uri                     = "arn:aws:apigateway:${var.aws_region}:sqs:path/${aws_sqs_queue.sgtm-webhooks-fifo.name}"
  # content_handling        = "CONVERT_TO_BINARY"
  request_parameters = {
    "integration.request.header.Content-Type" = "'application/x-www-form-urlencoded'"
  }

  request_templates = {
    "application/json" = <<EOT
#set($headers=$input.params().header)
#set($id=$headers.get("X-GitHub-Hook-ID"))
Action=SendMessage##
&MessageGroupId=$id##
&MessageDeduplicationId=$id##
&MessageAttributes.1.Name=X-GitHub-Event##
&MessageAttributes.1.Value.DataType=String##
&MessageAttributes.1.Value.StringValue=$util.urlEncode($headers.get("X-GitHub-Event"))##
&MessageAttributes.2.Name=X-Hub-Signature-256##
&MessageAttributes.2.Value.DataType=String##
&MessageAttributes.2.Value.StringValue=$util.urlEncode($headers.get("X-Hub-Signature-256"))##
&MessageAttributes.3.Name=X-GitHub-Delivery##
&MessageAttributes.3.Value.DataType=String##
&MessageAttributes.3.Value.StringValue=$util.urlEncode($headers.get("X-GitHub-Delivery"))##
&MessageBody=$input.body

EOT
  }
}

resource "aws_api_gateway_integration_response" "sgtm_proxy_response_for_sqs" {
  depends_on  = [aws_api_gateway_integration.sgtm_sqs_integration]
  rest_api_id = aws_api_gateway_rest_api.sgtm_rest_api_for_sqs.id
  resource_id = aws_api_gateway_resource.sgtm_resource_for_sqs.id
  http_method = aws_api_gateway_method.sgtm_post_for_sqs.http_method
  status_code = aws_api_gateway_method_response.proxy_for_sqs.status_code
}

resource "aws_sqs_queue" "sgtm-webhooks-fifo" {
  name                        = "sgtm-webhooks.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  visibility_timeout_seconds  = 720 # 12 minutes
  message_retention_seconds   = 3600 # 1 hr
}

# Gives the Lambda function permissions to read from SQS queue
resource "aws_iam_policy" "lambda-function-sqs-policy" {
policy = <<EOF
{
"Version" : "2012-10-17",
  "Statement" : [
    {
      "Effect" : "Allow",
      "Action" : [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes",
        "kms:Decrypt",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource" : ["${aws_sqs_queue.sgtm-webhooks-fifo.arn}"]
    }
  ]
}
EOF
}

resource "aws_lambda_event_source_mapping" "event_source_mapping" {
  event_source_arn = aws_sqs_queue.sgtm-webhooks-fifo.arn
  enabled          = false
  function_name    = aws_lambda_function.sgtm.function_name
}

resource "aws_iam_role_policy_attachment" "lambda-function-sqs" {
  role       = aws_iam_role.iam_for_lambda_function.name
  policy_arn = aws_iam_policy.lambda-function-sqs-policy.arn
}

# Gives the API Gateway permissions to send messages to the SQS queue
resource "aws_iam_policy" "api-gateway-sqs-policy" {
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
     {
      "Effect" : "Allow",
      "Action" : [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:PutLogEvents",
        "logs:GetLogEvents",
        "logs:FilterLogEvents"
      ],
      "Resource" : "*"
    },
    {
      "Effect": "Allow",
      "Resource": ["${aws_sqs_queue.sgtm-webhooks-fifo.arn}"],
      "Action": [
        "sqs:SendMessageBatch",
        "sqs:SendMessage"
      ]
    }
  ]
}
EOF
}

resource "aws_iam_role" "iam_for_api_gateway" {
  name = "iam_for_api_gateway"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "apigateway.amazonaws.com"
      },
      "Effect": "Allow"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "api-gateway-sqs-policy-attachment" {
  role       = aws_iam_role.iam_for_api_gateway.name
  policy_arn = aws_iam_policy.api-gateway-sqs-policy.arn
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

resource "aws_dynamodb_table" "sgtm-users" {
  name           = "sgtm-users"
  read_capacity  = 5
  write_capacity = 5
  hash_key       = "github/handle"

  attribute {
    name = "github/handle"
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
