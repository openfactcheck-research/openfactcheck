# ##############################################################################
# IAM Role — API Lambda
# ##############################################################################

resource "aws_iam_role" "lambda_api" {
  name = "openfactcheck-lambda-api-${terraform.workspace}-${var.aws_region}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name = "OpenFactCheck - Lambda API Role - ${terraform.workspace}"
  }
}

resource "aws_iam_role_policy" "lambda_api_logs" {
  name = "cloudwatch-logs"
  role = aws_iam_role.lambda_api.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "APIWriteLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${var.aws_account}:*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_api_dynamodb" {
  name = "dynamodb-access"
  role = aws_iam_role.lambda_api.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "APIReadWriteTables"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.openfactcheck.arn,
          "${aws_dynamodb_table.openfactcheck.arn}/index/*",
          aws_dynamodb_table.openfactcheck_users.arn,
          "${aws_dynamodb_table.openfactcheck_users.arn}/index/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_api_kms" {
  name = "kms-secrets"
  role = aws_iam_role.lambda_api.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "APIEncryptSecrets"
        Effect   = "Allow"
        Action   = "kms:Encrypt"
        Resource = aws_kms_key.users.arn
      },
      {
        Sid      = "APITableKeyAccess"
        Effect   = "Allow"
        Action   = ["kms:Decrypt", "kms:GenerateDataKey"]
        Resource = aws_kms_key.users.arn
        Condition = {
          StringEquals = {
            "kms:ViaService" = "dynamodb.${var.aws_region}.amazonaws.com"
          }
        }
      },
      {
        Sid      = "APIDecryptSecrets"
        Effect   = "Allow"
        Action   = ["kms:Decrypt", "kms:DescribeKey"]
        Resource = aws_kms_key.users.arn
      },
    ]
  })
}

