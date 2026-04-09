# ##############################################################################
# Locals
# ##############################################################################
locals {
  attributes = {
    root_domain     = "openfactcheck.com"
    certificate_arn = "arn:aws:acm:us-east-1:252286678527:certificate/bd2961d6-5a11-48d0-9ccc-c5e1f603ff09"
    route53_zone_id = "Z08124453UJZ86BMG3TNR"
  }

  certificate_arn = local.attributes.certificate_arn
  route53_zone_id = local.attributes.route53_zone_id
  root_domain     = local.attributes.root_domain
  api_domain      = terraform.workspace == "production" ? "api.${local.root_domain}" : "${terraform.workspace}-api.${local.root_domain}"
  frontend_origin = terraform.workspace == "production" ? "https://playground.${local.root_domain}" : "https://${terraform.workspace}-playground.${local.root_domain}"
  cors_origins    = [local.frontend_origin, "http://localhost:3001"]
}
