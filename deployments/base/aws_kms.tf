# ##############################################################################
# KMS Key — encrypts user secrets stored in the users table
# ##############################################################################

resource "aws_kms_key" "users" {
  description             = "OpenFactCheck user secrets encryption (${terraform.workspace})"
  enable_key_rotation     = true
  deletion_window_in_days = 30

  policy = jsonencode({
    Version = "2012-10-17"
    Id      = "users-key-least-privilege"
    Statement = concat([
      {
        Sid       = "KeyAdministration"
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::${var.aws_account}:root" }
        Action = [
          "kms:Create*",
          "kms:Describe*",
          "kms:Enable*",
          "kms:List*",
          "kms:Put*",
          "kms:Update*",
          "kms:Revoke*",
          "kms:Disable*",
          "kms:Get*",
          "kms:Delete*",
          "kms:TagResource",
          "kms:UntagResource",
          "kms:ScheduleKeyDeletion",
          "kms:CancelKeyDeletion",
          "kms:RotateKeyOnDemand",
        ]
        Resource = "*"
      },
      {
        Sid       = "APIEncryptSecrets"
        Effect    = "Allow"
        Principal = { AWS = aws_iam_role.lambda_api.arn }
        Action    = ["kms:Encrypt", "kms:DescribeKey"]
        Resource  = "*"
      },
      {
        Sid       = "APITableKeyAccess"
        Effect    = "Allow"
        Principal = { AWS = aws_iam_role.lambda_api.arn }
        Action    = ["kms:Decrypt", "kms:GenerateDataKey"]
        Resource  = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = "dynamodb.${var.aws_region}.amazonaws.com"
          }
        }
      },
      {
        Sid       = "APIDecryptSecrets"
        Effect    = "Allow"
        Principal = { AWS = aws_iam_role.lambda_api.arn }
        Action    = ["kms:Decrypt", "kms:DescribeKey"]
        Resource  = "*"
      },
      ], terraform.workspace == "production" ? [] : [
      {
        Sid       = "DevAdminAccess"
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::${var.aws_account}:root" }
        Action    = ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
        Resource  = "*"
      },
    ])
  })

  tags = {
    Name = "OpenFactCheck - Users KMS Key - ${terraform.workspace} - ${var.aws_region}"
  }
}

resource "aws_kms_alias" "users" {
  name          = "alias/openfactcheck-users-${terraform.workspace}-${var.aws_region}"
  target_key_id = aws_kms_key.users.key_id
}
