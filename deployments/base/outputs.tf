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

output "api_function_url" {
  description = "Lambda Function URL (origin; reachable only through CloudFront)"
  value       = aws_lambda_function_url.api.function_url
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution serving the API custom domain"
  value       = aws_cloudfront_distribution.api.id
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

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.api.function_name
}

output "api_url" {
  description = "API custom domain URL"
  value       = "https://${local.api_domain}"
}
