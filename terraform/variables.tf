variable "aws_region" {
  type        = string
  description = "The AWS region to create resources in"
  default     = "us-east-1"
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


variable "terraform_backend_s3_bucket_name" {
  type        = string
  default     = ""
  description = "S3 bucket name to store the Terraform state"
}

variable "terraform_backend_dynamodb_lock_table" {
  type        = string
  default     = ""
  description = "The DynamoDb table to store the Terraform state lock"
}

variable "terraform_backend_use_tfc" {
  type        = bool
  default     = false
  description = "Whether to use Terraform Cloud as the remote backend. Defaults to false."
}

variable "terraform_backend_tfc_organization" {
  type        = string
  default     = ""
  description = "The Terraform Cloud organization to use as the remote backend. Must be provided if terraform_backend_use_tfc is true."
}

variable "terraform_backend_tfc_workspace" {
  type        = string
  default     = ""
  description = "The Terraform Cloud workspace to use as the remote backend. Must be provided if terraform_backend_use_tfc is true."
}

variable "github_usernames_to_asana_gids_s3_path" {
  description = "The S3 path, in the form bucket/key, to the .json file that maps Github usernames to email addresses associated with Asana users."
  type        = string
}

variable "token_retrieval_lambda_arn" {
  description = "The ARN of the Lambda function that retrieves the GitHub token"
  default     = null
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
