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


variable "lambda_function_timeout" {
  type        = number
  description = "Timeout used for the AWS Lambda function"
  default     = 30
}


variable "terraform_backend_s3_bucket_name" {
  type        = string
  description = "S3 bucket name to store the Terraform state"
}

variable "terraform_backend_dynamodb_lock_table" {
  type        = string
  description = "The DynamoDb table to store the Terraform state lock"
}
