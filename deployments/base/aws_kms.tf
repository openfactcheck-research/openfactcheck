# ##############################################################################
# KMS Key — encrypts user secrets stored in the users table
# ##############################################################################

resource "aws_kms_key" "users" {
  description             = "OpenFactCheck user secrets encryption (${terraform.workspace})"
  enable_key_rotation     = true
  deletion_window_in_days = 30

  tags = {
    Name = "OpenFactCheck - Users KMS Key - ${terraform.workspace} - ${var.aws_region}"
  }
}

resource "aws_kms_alias" "users" {
  name          = "alias/openfactcheck-users-${terraform.workspace}-${var.aws_region}"
  target_key_id = aws_kms_key.users.key_id
}
