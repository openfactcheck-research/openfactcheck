# ##############################################################################
# Outputs
# ##############################################################################

output "github_oidc_provider_arn" {
  description = "GitHub OIDC Provider ARN"
  value       = aws_iam_openid_connect_provider.github.arn
}

output "github_actions_integration_role_arn" {
  description = "IAM Role ARN for GitHub Actions - Integration"
  value       = aws_iam_role.github_actions_integration.arn
}

output "github_actions_production_role_arn" {
  description = "IAM Role ARN for GitHub Actions - Production"
  value       = aws_iam_role.github_actions_production.arn
}
