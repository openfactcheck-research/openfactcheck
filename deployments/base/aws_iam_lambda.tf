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
          "${aws_dynamodb_table.openfactcheck.arn}/index/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_api_sfn" {
  name = "stepfunctions"
  role = aws_iam_role.lambda_api.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution",
          "states:DescribeExecution"
        ]
        Resource = [
          aws_sfn_state_machine.pipeline.arn,
          "${aws_sfn_state_machine.pipeline.arn}:*"
        ]
      }
    ]
  })
}

# ##############################################################################
# IAM Role — Engine Lambda
# ##############################################################################

resource "aws_iam_role" "lambda_engine" {
  name = "openfactcheck-lambda-engine-${terraform.workspace}-${var.aws_region}"

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
    Name = "OpenFactCheck - Lambda Engine Role - ${terraform.workspace}"
  }
}

resource "aws_iam_role_policy" "lambda_engine_logs" {
  name = "cloudwatch-logs"
  role = aws_iam_role.lambda_engine.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
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
