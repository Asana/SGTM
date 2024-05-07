locals {
  cluster_suffix = var.naming_cluster_suffix != null ? "_${var.naming_cluster_suffix}" : ""
}

provider "aws" {
  region = var.aws_region
}

resource "aws_cloudwatch_log_group" "main" {
  name = "/aws/lambda/${aws_lambda_function.sgtm.function_name}"
}
