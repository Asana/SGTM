provider "aws" {
  region = "us-east-1"
}

### LAMBDA

# TODO: Write custom policies that do just what we need rather than the broader
# AWS managed full access policies
data "aws_iam_policy" "AmazonDynamoDBFullAccess" {
  arn = "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
}

data "aws_iam_policy" "AWSLambdaBasicExecutionRole" {
  arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
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
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "lambda-function-dynamo-db-access" {
  role       = "${aws_iam_role.iam_for_lambda_function.name}"
  policy_arn = "${data.aws_iam_policy.AmazonDynamoDBFullAccess.arn}"
}

resource "aws_iam_role_policy_attachment" "lambda-function-basic-execution-role" {
  role       = "${aws_iam_role.iam_for_lambda_function.name}"
  policy_arn = "${data.aws_iam_policy.AWSLambdaBasicExecutionRole.arn}"
}

resource "aws_iam_role_policy_attachment" "lambda-function-api-keys" {
  role       = "${aws_iam_role.iam_for_lambda_function.name}"
  policy_arn = "${aws_iam_policy.LambdaFunctionApiKeysBucketAccess.arn}"
}

resource "aws_iam_policy" "LambdaFunctionApiKeysBucketAccess" {
  policy     = <<EOF
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
      "Effect": "Allow",
      "Sid": ""
    },
    {
      "Action": [
        "kms:Decrypt"
      ],
      "Resource": [
        "${aws_kms_key.api_encryption_key.arn}"
      ],
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_lambda_function" "sgtm" {
  filename      = "../build/function.zip"
  function_name = "sgtm"
  role          = "${aws_iam_role.iam_for_lambda_function.arn}"
  handler       = "src.handler.handler"

  # The filebase64sha256() function is available in Terraform 0.11.12 and later
  # For Terraform 0.11.11 and earlier, use the base64sha256() function and the file() function:
  # source_code_hash = "${base64sha256(file("lambda_function_payload.zip"))}"
  source_code_hash = "${filebase64sha256("../build/function.zip")}"

  runtime = "python3.7"

  timeout = var.lambda_function_timeout
  environment {
    variables = {
      API_KEYS_S3_BUCKET  = "${var.api_key_s3_bucket_name}",
      API_KEYS_S3_KEY     = "${var.api_key_s3_object}"
    }
  }

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
  rest_api_id = "${aws_api_gateway_rest_api.sgtm_rest_api.id}"
  parent_id   = "${aws_api_gateway_rest_api.sgtm_rest_api.root_resource_id}"
  path_part   = "sgtm"
}

resource "aws_api_gateway_method" "sgtm_post" {
  rest_api_id   = "${aws_api_gateway_rest_api.sgtm_rest_api.id}"
  resource_id   = "${aws_api_gateway_resource.sgtm_resource.id}"
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_deployment" "sgtm_deployment" {
  depends_on  = ["aws_api_gateway_integration.sgtm_lambda_integration"]
  rest_api_id = "${aws_api_gateway_rest_api.sgtm_rest_api.id}"
  stage_name  = "default"
}

resource "aws_api_gateway_method_response" "proxy" {
  rest_api_id = "${aws_api_gateway_rest_api.sgtm_rest_api.id}"
  resource_id = "${aws_api_gateway_resource.sgtm_resource.id}"
  http_method = "${aws_api_gateway_method.sgtm_post.http_method}"
  status_code = "200"
}

resource "aws_api_gateway_integration" "sgtm_lambda_integration" {
  rest_api_id             = "${aws_api_gateway_rest_api.sgtm_rest_api.id}"
  resource_id             = "${aws_api_gateway_resource.sgtm_resource.id}"
  http_method             = "${aws_api_gateway_method.sgtm_post.http_method}"
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = "${aws_lambda_function.sgtm.invoke_arn}"
}

resource "aws_api_gateway_integration_response" "sgtm_proxy_response" {
  depends_on = ["aws_api_gateway_integration.sgtm_lambda_integration"]
  rest_api_id = "${aws_api_gateway_rest_api.sgtm_rest_api.id}"
  resource_id = "${aws_api_gateway_resource.sgtm_resource.id}"
  http_method = "${aws_api_gateway_method.sgtm_post.http_method}"
  status_code = "${aws_api_gateway_method_response.proxy.status_code}"
}

resource "aws_lambda_permission" "lambda_permission_for_sgtm_rest_api" {
  statement_id  = "AllowSGTMAPIInvoke"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.sgtm.function_name}"
  principal     = "apigateway.amazonaws.com"

  # More: http://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-control-access-using-iam-policies-to-invoke-api.html
  source_arn = "${aws_api_gateway_rest_api.sgtm_rest_api.execution_arn}/*/${aws_api_gateway_method.sgtm_post.http_method}${aws_api_gateway_resource.sgtm_resource.path}"
}


### DYNAMODB

resource "aws_dynamodb_table" "sgtm-lock" {
  name           = "sgtm-lock"
  read_capacity  = 5
  write_capacity = 5
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
}

resource "aws_kms_key" "api_encryption_key" {
  description             = "This key is used to encrypt api key bucket objects"
  deletion_window_in_days = 10
}

resource "aws_s3_bucket" "api_key_bucket" {
  bucket = var.api_key_s3_bucket_name
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        kms_master_key_id = "${aws_kms_key.api_encryption_key.arn}"
        sse_algorithm     = "aws:kms"
      }
    }
  }
}


### Terraform backend

terraform {
  backend "s3" {
    bucket = "sgtm-terraform-state-bucket"
    key    = "terraform.tfstate"
    region = "us-east-1"
    dynamodb_table = "sgtm_terraform_state_lock"
  }
}

