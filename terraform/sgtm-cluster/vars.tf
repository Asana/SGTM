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

variable "naming_cluster_suffix" {
  description = "A cluster_suffix to append to the names of resources"
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

variable "github_app_name" {
  type        = string
  default     = null
  description = "The name of the Github app that will be used to authenticate with Github."
}

variable "github_app_installation_access_token_retrieval_url" {
  type        = string
  default     = null
  description = "The URL to retrieve a Github app installation access token from. This URL should accept a POST request with a JSON body that specifies a value for the 'github_app_name' key. The URL should return a JSON object with a 'token' key that contains the Github token, and an 'expires_at' key which contains a timestamp of the format '%Y-%m-%dT%H:%M:%SZ'."
}

variable "custom_config_bucket_name" {
  type        = string
  description = "The S3 bucket that stores custom configuration for your deployment of SGTM"
}
variable "custom_lambda_role_policy_s3_object_key" {
  type        = string
  default     = null
  description = "The S3 path within var.custom_config_bucket_name where the JSON-formatted custom Lambda role policy is stored. This object should be readable by the terragrunt and terraform process during the plan and apply steps."
}
