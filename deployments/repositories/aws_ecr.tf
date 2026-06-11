# ##############################################################################
# ECR Repository — Container images for Lambda
# ##############################################################################

resource "aws_ecr_repository" "openfactcheck_api" {
  name                 = "openfactcheck-api-${terraform.workspace}-${var.aws_region}"
  image_tag_mutability = "MUTABLE"
  force_delete         = terraform.workspace != "production"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "OpenFactCheck - ECR - API - ${terraform.workspace} - ${var.aws_region}"
  }
}

# Allow the Lambda service to pull images from this repo (fixes ImageAccessDenied).
resource "aws_ecr_repository_policy" "openfactcheck_api" {
  repository = aws_ecr_repository.openfactcheck_api.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "LambdaECRImageRetrievalPolicy"
        Effect    = "Allow"
        Principal = { Service = "lambda.amazonaws.com" }
        Action = [
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]
        Condition = {
          StringLike = {
            "aws:sourceArn" = "arn:aws:lambda:${var.aws_region}:${var.aws_account}:function:openfactcheck-*"
          }
        }
      }
    ]
  })
}

resource "aws_ecr_lifecycle_policy" "openfactcheck_api" {
  repository = aws_ecr_repository.openfactcheck_api.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 5 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 5
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# ##############################################################################
# ECR Repository — Engine (pipeline executor)
# ##############################################################################

resource "aws_ecr_repository" "openfactcheck_engine" {
  name                 = "openfactcheck-engine-${terraform.workspace}-${var.aws_region}"
  image_tag_mutability = "MUTABLE"
  force_delete         = terraform.workspace != "production"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "OpenFactCheck - ECR - Engine - ${terraform.workspace} - ${var.aws_region}"
  }
}

# Allow the Lambda service to pull images from this repo (fixes ImageAccessDenied).
resource "aws_ecr_repository_policy" "openfactcheck_engine" {
  repository = aws_ecr_repository.openfactcheck_engine.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "LambdaECRImageRetrievalPolicy"
        Effect    = "Allow"
        Principal = { Service = "lambda.amazonaws.com" }
        Action = [
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]
        Condition = {
          StringLike = {
            "aws:sourceArn" = "arn:aws:lambda:${var.aws_region}:${var.aws_account}:function:openfactcheck-*"
          }
        }
      }
    ]
  })
}

resource "aws_ecr_lifecycle_policy" "openfactcheck_engine" {
  repository = aws_ecr_repository.openfactcheck_engine.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 5 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 5
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
