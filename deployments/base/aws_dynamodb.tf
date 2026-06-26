# ##############################################################################
# DynamoDB Table — Single-table design with PK + SK
# ##############################################################################

resource "aws_dynamodb_table" "openfactcheck" {
  name         = "openfactcheck-db-${terraform.workspace}-${var.aws_region}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  deletion_protection_enabled = terraform.workspace == "production" ? true : false

  tags = {
    Name = "OpenFactCheck - DynamoDB - ${terraform.workspace} - ${var.aws_region}"
  }
}

# ##############################################################################
# DynamoDB Table — User settings and secrets (dedicated, KMS-encrypted)
# ##############################################################################

resource "aws_dynamodb_table" "openfactcheck_users" {
  name         = "openfactcheck-users-db-${terraform.workspace}-${var.aws_region}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.users.arn
  }

  deletion_protection_enabled = terraform.workspace == "production" ? true : false

  tags = {
    Name = "OpenFactCheck - Users DynamoDB - ${terraform.workspace} - ${var.aws_region}"
  }
}
