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
