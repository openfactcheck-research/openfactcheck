# ##############################################################################
# DynamoDB Table — Single-table design
# ##############################################################################

resource "aws_dynamodb_table" "openfactcheck" {
  name         = "openfactcheck-db-${terraform.workspace}-${var.aws_region}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"

  global_secondary_index {
    name            = "gs1"
    hash_key        = "GS1PK"
    projection_type = "ALL"
  }

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "GS1PK"
    type = "S"
  }

  deletion_protection_enabled = terraform.workspace == "production" ? true : false

  tags = {
    Name = "OpenFactCheck - DynamoDB - ${terraform.workspace} - ${var.aws_region}"
  }
}
