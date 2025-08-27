output "api_gateway_url" {
  description = "URL of the API Gateway"
  value       = "https://${aws_api_gateway_rest_api.leaderboard_api.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.leaderboard_stage.stage_name}"
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.leaderboard_function.function_name
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table"
  value       = aws_dynamodb_table.leaderboard_scores.name
}

output "api_gateway_rest_api_id" {
  description = "ID of the API Gateway REST API"
  value       = aws_api_gateway_rest_api.leaderboard_api.id
}

output "custom_domain_name" {
  description = "Custom domain name for the API"
  value       = aws_api_gateway_domain_name.api_domain.domain_name
}

output "custom_domain_target" {
  description = "Target domain name for the custom domain"
  value       = aws_api_gateway_domain_name.api_domain.regional_domain_name
}