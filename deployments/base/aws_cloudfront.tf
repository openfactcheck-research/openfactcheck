# ##############################################################################
# CloudFront — custom domain in front of the API Function URL
# ##############################################################################

data "aws_cloudfront_cache_policy" "disabled" {
  name = "Managed-CachingDisabled"
}

data "aws_cloudfront_origin_request_policy" "all_viewer_except_host" {
  name = "Managed-AllViewerExceptHostHeader"
}

resource "aws_cloudfront_distribution" "api" {
  enabled         = true
  is_ipv6_enabled = true
  comment         = "OpenFactCheck API - ${terraform.workspace} - ${var.aws_region}"
  aliases         = [local.api_domain]
  price_class     = "PriceClass_100"

  origin {
    domain_name = "${aws_lambda_function_url.api.url_id}.lambda-url.${var.aws_region}.on.aws"
    origin_id   = "api-function-url"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
      # A run streams events as they happen; the ceiling is time-to-first-byte, not total run length.
      origin_read_timeout = 60
    }
  }

  default_cache_behavior {
    target_origin_id         = "api-function-url"
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods           = ["GET", "HEAD"]
    cache_policy_id          = data.aws_cloudfront_cache_policy.disabled.id
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.all_viewer_except_host.id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = local.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = {
    Name = "OpenFactCheck - API CloudFront - ${terraform.workspace} - ${var.aws_region}"
  }
}
