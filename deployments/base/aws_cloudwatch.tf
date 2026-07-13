# ##############################################################################
# SNS Topic — Alarm notifications
# ##############################################################################

resource "aws_sns_topic" "alarms" {
  name = "openfactcheck-alarms-${terraform.workspace}-${var.aws_region}"

  tags = {
    Name = "OpenFactCheck - SNS Alarms - ${terraform.workspace} - ${var.aws_region}"
  }
}

resource "aws_sns_topic_subscription" "alarm_email" {
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = "hasaniqbal.dev@gmail.com"
}

# ##############################################################################
# Lambda Error Alarms
# ##############################################################################

resource "aws_cloudwatch_metric_alarm" "api_errors" {
  alarm_name          = "openfactcheck-api-errors-${terraform.workspace}"
  alarm_description   = "API Lambda error rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.api.function_name
  }

  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]

  tags = {
    Name = "OpenFactCheck - API Errors - ${terraform.workspace}"
  }
}

