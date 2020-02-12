variable "api_key_s3_bucket_name" {
  type        = string
  description = "Name of the API key S3 bucket"
  default     = "asana-sgtm-api-keys"
}


variable "lambda_function_timeout" {
  type        = number
  description = "Timeout used for the AWS Lambda function"
  default     = 30
}
