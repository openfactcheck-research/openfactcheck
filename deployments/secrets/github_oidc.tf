# ##############################################################################
# GitHub OIDC Provider
# Account-level resource — created once per AWS account
# ##############################################################################
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

# ##############################################################################
# IAM Role — Integration (main branch only)
# ##############################################################################
resource "aws_iam_role" "github_actions_integration" {
  name = "github-actions-openfactcheck-integration-${var.aws_region}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
            "token.actions.githubusercontent.com:sub" = [
              "repo:${var.github_org}/${var.github_repo_openfactcheck}:ref:refs/heads/main",
              "repo:${var.github_org}/${var.github_repo_playground}:ref:refs/heads/main",
            ]
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "github_actions_integration" {
  role       = aws_iam_role.github_actions_integration.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

# ##############################################################################
# IAM Role — Production (version tags only)
# ##############################################################################
resource "aws_iam_role" "github_actions_production" {
  name = "github-actions-openfactcheck-production-${var.aws_region}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = [
              "repo:${var.github_org}/${var.github_repo_openfactcheck}:ref:refs/tags/v*",
              "repo:${var.github_org}/${var.github_repo_playground}:ref:refs/tags/v*",
            ]
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "github_actions_production" {
  role       = aws_iam_role.github_actions_production.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}
