# ##############################################################################
# Outputs
# ##############################################################################

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = aws_cognito_user_pool.openfactcheck.id
}

output "cognito_user_pool_client_id" {
  description = "Cognito User Pool Client ID"
  value       = aws_cognito_user_pool_client.openfactcheck_client.id
}

output "api_gateway_url" {
  description = "API Gateway invoke URL"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "dynamodb_table_name" {
  description = "DynamoDB table name"
  value       = aws_dynamodb_table.openfactcheck.name
}

output "dynamodb_users_table_name" {
  description = "DynamoDB users table name (settings and secrets)"
  value       = aws_dynamodb_table.openfactcheck_users.name
}

output "users_kms_key_arn" {
  description = "KMS key ARN for user secrets encryption"
  value       = aws_kms_key.users.arn
}

output "ecr_repository_url" {
  description = "ECR repository URL for the API container image"
  value       = data.aws_ecr_repository.api.repository_url
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.api.function_name
}

output "api_url" {
  description = "API custom domain URL"
  value       = "https://${local.api_domain}"
}
