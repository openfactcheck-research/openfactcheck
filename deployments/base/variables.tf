variable "aws_profile" {
  description = "AWS profile for deployment"
  type        = string
}

variable "aws_region" {
  description = "AWS Region for deployment"
  type        = string
}

variable "aws_account" {
  description = "AWS Account ID for deployment"
  type        = string

  validation {
    condition     = length(var.aws_account) == 12 && can(regex("^[0-9]+$", var.aws_account))
    error_message = "AWS Account ID must be a 12-digit number."
  }
}

variable "aws_account_name" {
  description = "AWS Account Name for deployment (optional, for reference)"
  type        = string
}

variable "cors_origins" {
  description = "Allowed CORS origins for the API"
  type        = list(string)
  default     = ["http://localhost:3001"]
}

variable "build_version" {
  description = "Application build version (auto-set by build script)"
  type        = string
  default     = "unknown"
}

variable "commit" {
  description = "Git commit hash (auto-set by build script)"
  type        = string
  default     = "unknown"
}
