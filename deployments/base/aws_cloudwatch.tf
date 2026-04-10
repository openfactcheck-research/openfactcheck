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

resource "aws_cloudwatch_metric_alarm" "engine_errors" {
  alarm_name          = "openfactcheck-engine-errors-${terraform.workspace}"
  alarm_description   = "Engine Lambda error rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.engine.function_name
  }

  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]

  tags = {
    Name = "OpenFactCheck - Engine Errors - ${terraform.workspace}"
  }
}

# ##############################################################################
# Step Functions Alarm — failed pipeline executions
# ##############################################################################

resource "aws_cloudwatch_metric_alarm" "pipeline_failures" {
  alarm_name          = "openfactcheck-pipeline-failures-${terraform.workspace}"
  alarm_description   = "Step Functions pipeline execution failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  treat_missing_data  = "notBreaching"

  dimensions = {
    StateMachineArn = aws_sfn_state_machine.pipeline.arn
  }

  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]

  tags = {
    Name = "OpenFactCheck - Pipeline Failures - ${terraform.workspace}"
  }
}
