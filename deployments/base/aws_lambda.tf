# ##############################################################################
# ECR Data Source — repository lives in deployments/repositories
# ##############################################################################

data "aws_ecr_repository" "api" {
  name = "openfactcheck-api-${terraform.workspace}"
}

# ##############################################################################
# Lambda Function — API
# ##############################################################################

resource "aws_lambda_function" "api" {
  function_name = "openfactcheck-api-${terraform.workspace}-${var.aws_region}"
  description   = var.build_version
  role          = aws_iam_role.lambda_api.arn
  package_type  = "Image"
  image_uri     = "${data.aws_ecr_repository.api.repository_url}:latest"
  publish       = true
  timeout       = 30
  memory_size   = 256

  environment {
    variables = {
      OPENFACTCHECK_DATABASE_BACKEND     = "dynamodb"
      OPENFACTCHECK_DYNAMODB_TABLE_NAME  = aws_dynamodb_table.openfactcheck.name
      OPENFACTCHECK_DYNAMODB_REGION      = var.aws_region
      OPENFACTCHECK_COGNITO_REGION       = var.aws_region
      OPENFACTCHECK_COGNITO_USER_POOL_ID = aws_cognito_user_pool.openfactcheck.id
      OPENFACTCHECK_COGNITO_CLIENT_ID    = aws_cognito_user_pool_client.openfactcheck_client.id
      OPENFACTCHECK_CORS_ORIGINS         = jsonencode(var.cors_origins)
      OPENFACTCHECK_DEBUG                = "false"
      OPENFACTCHECK_AUTH_BYPASS          = "false"
    }
  }

  tags = {
    Name = "OpenFactCheck - Lambda API - ${terraform.workspace} - ${var.aws_region}"
  }

  lifecycle {
    ignore_changes = [image_uri]
  }
}

# ##############################################################################
# Lambda Alias — LIVE
# ##############################################################################

resource "aws_lambda_alias" "api_live" {
  name             = "LIVE"
  description      = "OpenFactCheck API Current Release"
  function_name    = aws_lambda_function.api.arn
  function_version = aws_lambda_function.api.version
}

# ##############################################################################
# Lambda Permissions — Allow API Gateway to invoke via LIVE alias
# ##############################################################################

resource "aws_lambda_permission" "api_gateway_default" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.openfactcheck.execution_arn}/*/$default"
  qualifier     = "LIVE"
}

resource "aws_lambda_permission" "api_gateway_proxy" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.openfactcheck.execution_arn}/*/*/{proxy+}"
  qualifier     = "LIVE"
}
