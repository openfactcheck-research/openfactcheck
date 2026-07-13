# ##############################################################################
# Lambda Function — API
# ##############################################################################

locals {
  api_zip = "${path.module}/../artifacts/api/build/api.zip"
}

resource "aws_lambda_function" "api" {
  function_name = "openfactcheck-api-${terraform.workspace}-${var.aws_region}"
  description   = var.build_version
  role          = aws_iam_role.lambda_api.arn

  package_type      = "Zip"
  runtime           = "python3.12"
  architectures     = ["arm64"]
  handler           = "run.sh"
  s3_bucket         = aws_s3_bucket.artifacts.id
  s3_key            = aws_s3_object.api.key
  s3_object_version = aws_s3_object.api.version_id
  source_code_hash  = filebase64sha256(local.api_zip)
  layers            = [local.lwa_layer_arn]
  publish           = true

  # Runs fact-check pipelines in-process for the streaming run endpoint, so it needs the
  # engine's headroom: the full Lambda timeout and the memory that keeps a run responsive.
  timeout     = 900
  memory_size = 2048

  # Snapshot the initialized environment when a version is published so cold invocations
  # resume from the snapshot instead of starting the runtime and app from scratch.
  snap_start {
    apply_on = "PublishedVersions"
  }

  environment {
    variables = {
      # Lambda Web Adapter: wrap the runtime, stream responses, and gate readiness on /health.
      AWS_LAMBDA_EXEC_WRAPPER      = "/opt/bootstrap"
      AWS_LWA_INVOKE_MODE          = "response_stream"
      AWS_LWA_READINESS_CHECK_PATH = "/health"
      PORT                         = "8080"

      OPENFACTCHECK_MODE                      = "cloud"
      OPENFACTCHECK_DYNAMODB_TABLE_NAME       = aws_dynamodb_table.openfactcheck.name
      OPENFACTCHECK_DYNAMODB_USERS_TABLE_NAME = aws_dynamodb_table.openfactcheck_users.name
      OPENFACTCHECK_SECRETS_KMS_KEY_ID        = aws_kms_key.users.arn
      OPENFACTCHECK_DYNAMODB_REGION           = var.aws_region
      OPENFACTCHECK_COGNITO_REGION            = var.aws_region
      OPENFACTCHECK_COGNITO_USER_POOL_ID      = aws_cognito_user_pool.openfactcheck.id
      OPENFACTCHECK_COGNITO_CLIENT_ID         = aws_cognito_user_pool_client.openfactcheck_client.id
      OPENFACTCHECK_CORS_ORIGINS              = jsonencode(local.cors_origins)
      OPENFACTCHECK_EXTERNAL_HOST             = local.api_domain
      OPENFACTCHECK_DEBUG                     = "false"
      OPENFACTCHECK_AUTH_BYPASS               = "false"
    }
  }

  tags = {
    Name = "OpenFactCheck - Lambda API - ${terraform.workspace} - ${var.aws_region}"
  }
}

# ##############################################################################
# Function URL — streamed via the Lambda Web Adapter, fronted by CloudFront
# ##############################################################################

resource "aws_lambda_function_url" "api" {
  function_name      = aws_lambda_function.api.function_name
  qualifier          = aws_lambda_alias.api_live.name
  authorization_type = "NONE"
  invoke_mode        = "RESPONSE_STREAM"

  # With authorization_type NONE the provider auto-adds the public-access permissions
  # (lambda:InvokeFunctionUrl plus lambda:InvokeFunction via the URL), so no separate
  # aws_lambda_permission is needed. Replacing the function cascade-deletes the URL and
  # those permissions server-side, so recreate the URL with it for a consistent apply.
  lifecycle {
    replace_triggered_by = [aws_lambda_function.api]
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
