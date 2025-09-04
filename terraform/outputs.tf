output "api_gateway_prod_invoke_url" {
  value = module.sgtm-prod.api_gateway_stage_invoke_url
}

output "api_gateway_staging_invoke_url" {
  value = module.sgtm-staging.api_gateway_stage_invoke_url
}
