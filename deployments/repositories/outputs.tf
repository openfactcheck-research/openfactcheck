# ##############################################################################
# Outputs
# ##############################################################################

output "ecr_repository_url_api" {
  description = "ECR repository URL for the API container image"
  value       = aws_ecr_repository.openfactcheck_api.repository_url
}
