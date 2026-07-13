# ##############################################################################
# S3 — versioned artifact repository for the Lambda deployment zip
# ##############################################################################

resource "aws_s3_bucket" "artifacts" {
  bucket = "openfactcheck-artifacts-${terraform.workspace}-${var.aws_region}"

  force_destroy = terraform.workspace != "production"

  tags = {
    Name = "OpenFactCheck - Artifacts - ${terraform.workspace} - ${var.aws_region}"
  }
}

resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket                  = aws_s3_bucket.artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  # The current object is the live artifact; superseded versions are rollback targets
  # that age out, and abandoned multipart uploads are cleaned up.
  rule {
    id     = "expire-superseded-artifacts"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 90
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# The deployment artifact. A new object version is created only when the zip's content
# changes; the function pins the exact version it deploys (see aws_lambda.tf).
resource "aws_s3_object" "api" {
  bucket      = aws_s3_bucket.artifacts.id
  key         = "api/api.zip"
  source      = local.api_zip
  source_hash = filemd5(local.api_zip)

  depends_on = [aws_s3_bucket_versioning.artifacts]
}
