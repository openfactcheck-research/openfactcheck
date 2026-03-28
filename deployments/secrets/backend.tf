# ##############################################################################
# Workspace Validation
# ##############################################################################
resource "terraform_data" "workspace_validation" {
  lifecycle {
    precondition {
      condition     = terraform.workspace != "default"
      error_message = "Workspace must not be default"
    }
  }
}

# ##############################################################################
# Backend
# ##############################################################################
terraform {
  required_version = ">=1.11.5"

  backend "s3" {
    key                  = "openfactcheck-secrets/terraform.tfstate"
    workspace_key_prefix = "openfactcheck-secrets"
  }

  required_providers {
    aws = {
      version = ">=6.32.0"
      source  = "hashicorp/aws"
    }
  }
}

# ##############################################################################
# Provider Configuration
# ##############################################################################
provider "aws" {
  region              = var.aws_region
  profile             = var.aws_profile
  allowed_account_ids = [var.aws_account]

  default_tags {
    tags = {
      Module        = "OpenFactCheck"
      Owner         = "OpenFactCheck Research"
      Creator       = "openfactcheck@gmail.com"
      ManagedBy     = "terraform"
      TerraformPath = "deployments/secrets"
      Region        = var.aws_region
    }
  }
}

# ##############################################################################
# Data Sources
# ##############################################################################
data "aws_caller_identity" "self" {}
