# ##############################################################################
# API Gateway HTTP API (v2)
# ##############################################################################

resource "aws_apigatewayv2_api" "openfactcheck" {
  name          = "openfactcheck-api-${terraform.workspace}-${var.aws_region}"
  description   = "OpenFactCheck API Gateway for ${terraform.workspace}-${var.aws_region}"
  protocol_type = "HTTP"

  disable_execute_api_endpoint = true

  cors_configuration {
    allow_origins     = var.cors_origins
    allow_methods     = ["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"]
    allow_headers     = ["Authorization", "Content-Type", "X-Request-ID"]
    allow_credentials = true
    max_age           = 3600
  }

  tags = {
    Name = "OpenFactCheck - API Gateway - ${terraform.workspace} - ${var.aws_region}"
  }
}

# ##############################################################################
# Integration — Lambda proxy via LIVE alias
# ##############################################################################

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.openfactcheck.id
  description            = "OpenFactCheck API Lambda for ${terraform.workspace}-${var.aws_region}"
  integration_type       = "AWS_PROXY"
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_uri        = aws_lambda_alias.api_live.invoke_arn
  payload_format_version = "2.0"
}

# ##############################################################################
# Routes
# ##############################################################################

resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.openfactcheck.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "options" {
  api_id             = aws_apigatewayv2_api.openfactcheck.id
  route_key          = "OPTIONS /{proxy+}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorization_type = "NONE"
}


# ##############################################################################
# Stage — auto-deploy with access logging
# ##############################################################################

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.openfactcheck.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api.arn
    format          = <<JSON
  { "requestTime": "$context.requestTime", "requestId": "$context.requestId", "httpMethod": "$context.httpMethod", "path": "$context.path", "routeKey": "$context.routeKey", "status": $context.status, "responseLatency": $context.responseLatency, "integrationRequestId": "$context.integration.requestId", "functionResponseStatus": "$context.integration.status", "integrationLatency": "$context.integration.latency", "integrationServiceStatus": "$context.integration.integrationStatus", "ip": "$context.identity.sourceIp", "userAgent": "$context.identity.userAgent", "error": { "message": "$context.error.message", "responseType": "$context.error.responseType" } }
  JSON
  }

  tags = {
    Name = "OpenFactCheck - API Gateway Stage - ${terraform.workspace} - ${var.aws_region}"
  }
}

# ##############################################################################
# Custom Domain
# ##############################################################################

resource "aws_apigatewayv2_domain_name" "api" {
  domain_name = local.api_domain

  domain_name_configuration {
    certificate_arn = local.certificate_arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }

  tags = {
    Name = "OpenFactCheck - API Domain - ${terraform.workspace} - ${var.aws_region}"
  }
}

resource "aws_apigatewayv2_api_mapping" "api" {
  api_id      = aws_apigatewayv2_api.openfactcheck.id
  domain_name = aws_apigatewayv2_domain_name.api.id
  stage       = aws_apigatewayv2_stage.default.id
}

# ##############################################################################
# API Gateway Logs
# ##############################################################################

resource "aws_cloudwatch_log_group" "api" {
  name              = "/openfactcheck-${terraform.workspace}-${var.aws_region}/api/"
  retention_in_days = 30

  tags = {
    Name = "OpenFactCheck - CloudWatch - API - ${terraform.workspace} - ${var.aws_region}"
  }
}
