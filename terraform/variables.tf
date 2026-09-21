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

variable "sgtm_feature__automerge_enabled" {
  type        = string
  description = "'true' if behavior to automerge pull requests with Github labels is enabled"
  default     = "false"
}

variable "sgtm_feature__automerge_disabled_repositories" {
  type        = string
  description = "A comma-separated list of Github repositories in format owner/repo that should not use the automerge feature"
  default     = ""
}

variable "sgtm_feature__excluded_attachment_sources_urls" {
  type        = string
  description = "A comma-separated list of URL hosts or substrings for which attachments should be excluded (e.g. example.com, sub.domain.com)."
  default     = ""
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

variable "sgtm_feature__sync_github_labels_enabled" {
  type        = string
  description = "'true' if behavior to sync GitHub labels to 'Labels (SGTM)' custom field is enabled"
  default     = "false"
}

variable "sgtm_feature__graphite_link_enabled" {
  type        = string
  description = "'true' if behavior to include Graphite link in Asana task is enabled"
  default     = "false"
}

variable "sgtm_feature__skip_team_slug" {
  type        = string
  description = "GitHub team slug whose members should skip Asana task creation. Leave empty to disable."
  default     = ""
}

variable "sgtm_feature__codeowner_tasks_enabled" {
  type        = string
  description = "'true' to create one Asana subtask per group of codeowners when a PR author adds the codeowner-tasks label. See docs/codeowner_tasks.md."
  default     = "false"
}

variable "sgtm_feature__codeowner_tasks_project_id" {
  type        = string
  description = "Asana project gid that codeowner subtasks are multi-homed into; it carries the subtask custom fields. Created by scripts/setup_sgtm_tasks_project.py --codeowner-project."
  default     = ""
}

variable "sgtm_feature__codeowner_tasks_opt_in_s3_path" {
  type        = string
  description = "S3 path, in the form bucket/key, of a JSON list of GitHub logins who opted in to the heads-up PR comment. Leave empty to post no heads-up comments."
  default     = ""
}

variable "sgtm_feature__codeowner_tasks_label" {
  type        = string
  description = "GitHub label a PR author adds to have SGTM create and route codeowner tasks. SGTM creates the label in the repository on first use."
  default     = "assign-tasks-to-codeowners"
}

variable "sgtm_feature__codeowner_tasks_idle_business_days" {
  type        = string
  description = "Business days a codeowner subtask assignee may go without reviewing before SGTM reassigns the subtask to another codeowner."
  default     = "1"
}

variable "sgtm_feature__codeowner_tasks_asana_workspace_id" {
  type        = string
  description = "Asana workspace gid used for out-of-office lookups when picking codeowner subtask assignees."
  default     = ""
}

variable "sgtm_feature__codeowner_tasks_docs_url" {
  type        = string
  description = "URL of the codeowner tasks documentation linked from PR comments and task footers."
  default     = "https://github.com/Asana/SGTM/blob/master/docs/codeowner_tasks.md"
}

variable "sgtm_feature__codeowner_tasks_org_docs_url" {
  type        = string
  description = "Optional URL of your organization's CODEOWNERS documentation, linked next to the SGTM docs."
  default     = ""
}

variable "sgtm_feature__codeowner_tasks_opt_in_command" {
  type        = string
  description = "Optional command engineers run to opt in to the heads-up comment, shown in PR comments and task footers (for example 'z sgtm codeowner-tasks opt-in')."
  default     = ""
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
