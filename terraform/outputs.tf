output "api_gateway_deployment_invoke_url" {
 value = "${aws_api_gateway_deployment.sgtm_deployment.invoke_url}/${aws_api_gateway_resource.sgtm_resource.path_part}"
}
