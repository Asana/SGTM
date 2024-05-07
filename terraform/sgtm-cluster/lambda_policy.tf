#### Create the SGTM lambda's role

data "aws_iam_policy_document" "assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "sgtm_lambda" {
  name               = "sgtm_lambda_role${local.cluster_suffix}"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}

#### Create a role policy document with all the permissions needed for the SGTM Lambda function
data "aws_iam_policy_document" "sgtm_lambda" {
  ##################################################################################################
  ##### DynamoDB Permissions
  ##################################################################################################
  # Give the Lambda function permissions to read/wrte from the locks DynamoDb table
  statement {
    sid = "DynamoDBSGTMLocks"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:Scan",
      "dynamodb:PutItem",
      "dynamodb:BatchWriteItem",
      "dynamodb:DeleteItem",
      "dynamodb:UpdateItem",
    ]
    resources = [
      var.dynamodb-sgtm-lock-arn,
    ]
  }

  # Give the Lambda function permissions to read/write from the DynamoDb objects table
  statement {
    sid = "DynamoDBSGTMObjects"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:Scan",
      "dynamodb:PutItem",
      "dynamodb:BatchWriteItem",
    ]
    resources = [
      var.dynamodb-sgtm-objects-arn,
    ]
  }

  ##################################################################################################
  ##### CloudWatch Logs Permissions
  ##################################################################################################

  # Gives the Lambda function permissions to create cloudwatch logs
  statement {
    sid = "CloudWatchLogs"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = [
      "${aws_cloudwatch_log_group.main.arn}:*",
    ]
  }


  ##################################################################################################
  ##### API Keys S3 Bucket Permissions
  ##################################################################################################

  # Give the Lambda function permissions to read from the API keys S3 bucket
  statement {
    sid = "S3APIKeys"
    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion",
    ]
    resources = [
      "${var.s3_api_key_bucket_arn}/${var.api_key_s3_object}",
    ]
  }
  # Give the Lambda function permissions to use the KMS key to decrypt the API keys 
  statement {
    sid = "DecryptAPIKeys"
    actions = [
      "kms:Decrypt",
    ]
    resources = [
      var.api_encryption_key_arn,
    ]
  }

  ##################################################################################################
  ##### SQS Permissions
  ##################################################################################################

  # Give the Lambda function permissions to send, receive, and delete messages from the SQS queue,
  # and to get the queue attributes
  statement {
    sid = "SQSSendMessage"
    actions = [
      "sqs:SendMessage",
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes"

    ]
    resources = [
      aws_sqs_queue.sgtm-webhooks-queue-fifo.arn,
    ]
  }

  ##################################################################################################
  ##### Github usernames to Asana GIDs S3 Bucket Permissions
  ##################################################################################################

  # Give the Lambda function permissions to read from the users file path at
  # var.github_usernames_to_asana_gids_s3_path
  statement {
    sid = "S3GithubUsernamesToAsanaGIDS"
    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion",
    ]
    resources = [
      "arn:aws:s3:::${var.github_usernames_to_asana_gids_s3_path}",
    ]
  }
}


#### Create a role policy in AWS with the permissions defined in the policy document
resource "aws_iam_policy" "sgtm_lambda" {
  name        = "sgtm_lambda_policy${local.cluster_suffix}"
  description = "Policy for the SGTM Lambda function"
  policy      = data.aws_iam_policy_document.sgtm_lambda.json
}


#### Attach the policy to the Lambda role! yay!
resource "aws_iam_role_policy_attachment" "sgtm_lambda" {
  role       = aws_iam_role.sgtm_lambda.name
  policy_arn = aws_iam_policy.sgtm_lambda.arn
}



##################################################################################################
##### Optional: Custom Lambda Role Policy
# If the custom_lambda_role_policy_s3_object_key is provided, then load the policy from the S3 path,
# create a policy in AWs, and attach the policy to the lambda role.
##################################################################################################

data "aws_s3_object" "additional_lambda_permissions" {
  count  = var.custom_lambda_role_policy_s3_object_key != null ? 1 : 0
  bucket = var.custom_config_bucket_name
  key    = var.custom_lambda_role_policy_s3_object_key
}

resource "aws_iam_policy" "additional_lambda_permissions" {
  count  = var.custom_lambda_role_policy_s3_object_key != null ? 1 : 0
  name   = "${var.naming_cluster_suffix}_additional_lambda_permissions"
  policy = data.aws_s3_object.additional_lambda_permissions[0].body
}

resource "aws_iam_role_policy_attachment" "additional_lambda_permissions" {
  count      = var.custom_lambda_role_policy_s3_object_key != null ? 1 : 0
  role       = aws_iam_role.sgtm_lambda.name
  policy_arn = aws_iam_policy.additional_lambda_permissions[0].arn
}

