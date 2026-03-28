# ##############################################################################
# User Pool
# ##############################################################################

resource "aws_cognito_user_pool" "openfactcheck" {
  name = "openfactcheck-${terraform.workspace}-${var.aws_region}"

  # Users sign in with email as their username (instead of a separate username)
  username_attributes = ["email"]

  # Email is auto-verified when user confirms the code (OTP) sent during signup
  auto_verified_attributes = ["email"]

  # Treat User@email.com and user@email.com as the same user
  username_configuration {
    case_sensitive = false
  }

  # Custom attribute for user preferences (JSON string)
  schema {
    name                = "preferences"
    attribute_data_type = "String"
    mutable             = true
    required            = false

    string_attribute_constraints {
      min_length = 0
      max_length = 2048
    }
  }

  # Password policy
  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  # Account recovery
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # Custom email templates
  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_subject        = "Your OpenFactCheck verification code"
    email_message        = <<-EOF
      <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
          <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #005355; margin: 0;">OpenFactCheck</h1>
          </div>
          <p style="font-size: 16px; color: #333;">Welcome to OpenFactCheck!</p>
          <p style="font-size: 16px; color: #333;">Your verification code is:</p>
          <div style="background: #f5f5f5; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0;">
            <span style="font-size: 32px; font-weight: bold; letter-spacing: 4px; color: #005355;">{####}</span>
          </div>
          <p style="font-size: 14px; color: #666;">This code expires in 24 hours.</p>
          <p style="font-size: 14px; color: #666;">If you didn't request this, please ignore this email.</p>
          <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
          <p style="font-size: 12px; color: #999; text-align: center;">OpenFactCheck - Fact-checking made easy</p>
        </body>
      </html>
    EOF
  }

  # Deletion protection
  deletion_protection = terraform.workspace == "production" ? "ACTIVE" : "INACTIVE"

  tags = {
    Name = "OpenFactCheck - ${terraform.workspace}"
  }
}

# ##############################################################################
# User Pool Client
# ##############################################################################
resource "aws_cognito_user_pool_client" "openfactcheck_client" {
  name         = "openfactcheck-client-${terraform.workspace}-${var.aws_region}"
  user_pool_id = aws_cognito_user_pool.openfactcheck.id

  # No secret needed for public clients (e.g. single-page apps)
  generate_secret = false

  # Authentication flows this client supports:
  # - ALLOW_USER_SRP_AUTH: Secure password auth without sending password over the wire
  # - ALLOW_REFRESH_TOKEN_AUTH: Allow refreshing access tokens without re-authenticating
  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]

  # Allow reading and writing custom attributes
  read_attributes  = ["email", "name", "custom:preferences"]
  write_attributes = ["email", "name", "custom:preferences"]

  # Token validity settings
  access_token_validity  = 1  # 1 hour
  id_token_validity      = 1  # 1 hour
  refresh_token_validity = 30 # 30 days

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }
}
