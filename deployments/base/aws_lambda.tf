# ##############################################################################
# ECR Data Source — repository lives in deployments/repositories
# ##############################################################################

data "aws_ecr_repository" "api" {
  name = "openfactcheck-api-${terraform.workspace}"
}

data "aws_ecr_image" "api" {
  repository_name = data.aws_ecr_repository.api.name
  image_tag       = "latest"
}

# ##############################################################################
# Lambda Function — API
# ##############################################################################

resource "aws_lambda_function" "api" {
  function_name    = "openfactcheck-api-${terraform.workspace}-${var.aws_region}"
  description      = var.build_version
  role             = aws_iam_role.lambda_api.arn
  package_type     = "Image"
  image_uri        = "${data.aws_ecr_repository.api.repository_url}:latest"
  source_code_hash = split(":", data.aws_ecr_image.api.image_digest)[1]
  publish          = true
  timeout          = 30
  memory_size      = 256

  environment {
    variables = {
      OPENFACTCHECK_MODE                 = "cloud"
      OPENFACTCHECK_DYNAMODB_TABLE_NAME  = aws_dynamodb_table.openfactcheck.name
      OPENFACTCHECK_DYNAMODB_REGION      = var.aws_region
      OPENFACTCHECK_COGNITO_REGION       = var.aws_region
      OPENFACTCHECK_COGNITO_USER_POOL_ID = aws_cognito_user_pool.openfactcheck.id
      OPENFACTCHECK_COGNITO_CLIENT_ID    = aws_cognito_user_pool_client.openfactcheck_client.id
      OPENFACTCHECK_CORS_ORIGINS         = jsonencode(local.cors_origins)
      OPENFACTCHECK_STATE_MACHINE_ARN     = aws_sfn_state_machine.pipeline.arn
      OPENFACTCHECK_DEBUG                = "false"
      OPENFACTCHECK_AUTH_BYPASS          = "false"
    }
  }

  tags = {
    Name = "OpenFactCheck - Lambda API - ${terraform.workspace} - ${var.aws_region}"
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

# ##############################################################################
# ECR Data Source — Engine
# ##############################################################################

data "aws_ecr_repository" "engine" {
  name = "openfactcheck-engine-${terraform.workspace}"
}

data "aws_ecr_image" "engine" {
  repository_name = data.aws_ecr_repository.engine.name
  image_tag       = "latest"
}

# ##############################################################################
# Lambda Function — Engine (Step Functions-invoked pipeline executor)
# ##############################################################################

resource "aws_lambda_function" "engine" {
  function_name    = "openfactcheck-engine-${terraform.workspace}-${var.aws_region}"
  description      = var.build_version
  role             = aws_iam_role.lambda_engine.arn
  package_type     = "Image"
  image_uri        = "${data.aws_ecr_repository.engine.repository_url}:latest"
  source_code_hash = split(":", data.aws_ecr_image.engine.image_digest)[1]
  publish          = true
  timeout          = 900 # 15 min — max Lambda timeout for long pipelines
  memory_size      = 512

  tags = {
    Name = "OpenFactCheck - Lambda Engine - ${terraform.workspace} - ${var.aws_region}"
  }
}

# ##############################################################################
# Lambda Alias — Engine LIVE
# ##############################################################################

resource "aws_lambda_alias" "engine_live" {
  name             = "LIVE"
  description      = "OpenFactCheck Engine Current Release"
  function_name    = aws_lambda_function.engine.arn
  function_version = aws_lambda_function.engine.version
}
