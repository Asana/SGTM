resource "aws_api_gateway_resource" "sgtm_resource" {
  rest_api_id = var.sgtm_rest_api_id
  parent_id   = var.sgtm_rest_api_root_resource_id
  path_part   = "sgtm${local.cluster}"
}

resource "aws_api_gateway_integration" "sgtm_lambda_integration" {
  rest_api_id             = var.sgtm_rest_api_id
  resource_id             = aws_api_gateway_resource.sgtm_resource.id
  http_method             = aws_api_gateway_method.sgtm_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.sgtm.invoke_arn
}

resource "aws_api_gateway_integration_response" "sgtm_proxy_response" {
  depends_on  = [aws_api_gateway_integration.sgtm_lambda_integration]
  rest_api_id = var.sgtm_rest_api_id
  resource_id = aws_api_gateway_resource.sgtm_resource.id
  http_method = aws_api_gateway_method.sgtm_post.http_method
  status_code = aws_api_gateway_method_response.proxy.status_code
}

resource "aws_api_gateway_method" "sgtm_post" {
  rest_api_id   = var.sgtm_rest_api_id
  resource_id   = aws_api_gateway_resource.sgtm_resource.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_deployment" "sgtm_deployment" {
  depends_on  = [aws_api_gateway_integration.sgtm_lambda_integration]
  rest_api_id = var.sgtm_rest_api_id
}

resource "aws_api_gateway_method_response" "proxy" {
  rest_api_id = var.sgtm_rest_api_id
  resource_id = aws_api_gateway_resource.sgtm_resource.id
  http_method = aws_api_gateway_method.sgtm_post.http_method
  status_code = "200"
}

resource "aws_api_gateway_stage" "sgtm_stage" {
  deployment_id = aws_api_gateway_deployment.sgtm_deployment.id
  rest_api_id = var.sgtm_rest_api_id
  stage_name = var.cluster != null ? "${var.cluster}" : "default"
}

output "api_gateway_stage_invoke_url" {
  value = "${aws_api_gateway_stage.sgtm_stage.invoke_url}/${aws_api_gateway_resource.sgtm_resource.path_part}"
}

### Create the SQS queue
resource "aws_sqs_queue" "sgtm-webhooks-queue-fifo" {
  name                        = "sgtm-webhooks-queue${local.cluster}.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  visibility_timeout_seconds  = 240  # 4 minutes
  message_retention_seconds   = 1800 # 30 minutes
}

resource "aws_lambda_event_source_mapping" "sgtm-sqs-source" {
  event_source_arn = aws_sqs_queue.sgtm-webhooks-queue-fifo.arn
  function_name    = aws_lambda_function.sgtm.function_name
  batch_size       = 1
}

resource "aws_lambda_permission" "lambda_permission_for_sgtm_rest_api" {
  statement_id  = "AllowSGTMAPIInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sgtm.function_name
  principal     = "apigateway.amazonaws.com"

  # More: http://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-control-access-using-iam-policies-to-invoke-api.html
  source_arn = "${var.sgtm_rest_api_execution_arn}/*/${aws_api_gateway_method.sgtm_post.http_method}${aws_api_gateway_resource.sgtm_resource.path}"
}
