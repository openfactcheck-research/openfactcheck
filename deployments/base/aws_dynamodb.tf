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
