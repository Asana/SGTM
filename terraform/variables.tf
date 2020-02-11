variable "asana_api_key" {
  type        = string
  description = "Asana API key to interact with the Asana API"
}

variable "github_api_key" {
  type        = string
  description = "GitHub API key to interact with the GitHub API"
}

variable "lambda_function_timeout" {
  type        = number
  description = "Timeout used for the AWS Lambda function"
  default     = 30
}
