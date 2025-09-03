locals {
  cluster = var.cluster != null ? "_${var.cluster}" : ""
}

provider "aws" {
  region = var.aws_region
}

resource "aws_cloudwatch_log_group" "main" {
  name = "/aws/lambda/${aws_lambda_function.sgtm.function_name}"
}
