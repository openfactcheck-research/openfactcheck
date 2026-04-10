# ##############################################################################
# Step Functions — Pipeline execution
#
# SetRunning → ExecutePipeline → SetResult (completed or failed)
# On Lambda error (timeout/OOM): Catch → SetFailed
#
# Writes execution state to workspace.execution in DynamoDB.
# ##############################################################################

resource "aws_sfn_state_machine" "pipeline" {
  name     = "openfactcheck-pipeline-${terraform.workspace}-${var.aws_region}"
  role_arn = aws_iam_role.sfn_pipeline.arn

  definition = jsonencode({
    Comment = "Execute a Blockly pipeline and write results to workspace"
    StartAt = "SetRunning"

    States = {
      SetRunning = {
        Type     = "Task"
        Resource = "arn:aws:states:::dynamodb:updateItem"
        Parameters = {
          TableName = aws_dynamodb_table.openfactcheck.name
          Key = {
            "PK" = { "S.$" = "States.Format('USER#{}#PROJECT#{}', $.user_id, $.project_id)" }
            "SK" = { "S.$" = "States.Format('WORKSPACE#{}', $.workspace_id)" }
          }
          UpdateExpression     = "SET #run = :run, updatedAt = :now"
          ExpressionAttributeNames = {
            "#run" = "run"
          }
          ExpressionAttributeValues = {
            ":run" = {
              "M" = {
                "status"    = { "S" = "running" }
                "output"    = { "S" = "" }
                "error"     = { "S" = "" }
                "startedAt" = { "S.$" = "$$.State.EnteredTime" }
              }
            }
            ":now" = { "S.$" = "$$.State.EnteredTime" }
          }
        }
        ResultPath = null
        Next       = "ExecutePipeline"
      }

      ExecutePipeline = {
        Type           = "Task"
        Resource       = "arn:aws:states:::lambda:invoke"
        TimeoutSeconds = 960
        Parameters = {
          FunctionName = "${aws_lambda_function.engine.arn}:$LATEST"
          "Payload.$"  = "$"
        }
        ResultSelector = {
          "success.$" = "$.Payload.success"
          "output.$"  = "$.Payload.output"
          "error.$"   = "$.Payload.error"
        }
        ResultPath = "$.result"
        Retry = [
          {
            ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 2
            MaxAttempts     = 2
            BackoffRate     = 2
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            ResultPath  = "$.error_info"
            Next        = "SetFailed"
          }
        ]
        Next = "CheckResult"
      }

      CheckResult = {
        Type = "Choice"
        Choices = [
          {
            Variable      = "$.result.success"
            BooleanEquals = true
            Next          = "SetCompleted"
          }
        ]
        Default = "SetFailedFromResult"
      }

      SetCompleted = {
        Type     = "Task"
        Resource = "arn:aws:states:::dynamodb:updateItem"
        Parameters = {
          TableName = aws_dynamodb_table.openfactcheck.name
          Key = {
            "PK" = { "S.$" = "States.Format('USER#{}#PROJECT#{}', $.user_id, $.project_id)" }
            "SK" = { "S.$" = "States.Format('WORKSPACE#{}', $.workspace_id)" }
          }
          UpdateExpression     = "SET #run = :run, updatedAt = :now"
          ExpressionAttributeNames = {
            "#run" = "run"
          }
          ExpressionAttributeValues = {
            ":run" = {
              "M" = {
                "status"      = { "S" = "completed" }
                "output"      = { "S.$" = "$.result.output" }
                "error"       = { "S" = "" }
                "completedAt" = { "S.$" = "$$.State.EnteredTime" }
              }
            }
            ":now" = { "S.$" = "$$.State.EnteredTime" }
          }
        }
        End = true
      }

      SetFailedFromResult = {
        Type     = "Task"
        Resource = "arn:aws:states:::dynamodb:updateItem"
        Parameters = {
          TableName = aws_dynamodb_table.openfactcheck.name
          Key = {
            "PK" = { "S.$" = "States.Format('USER#{}#PROJECT#{}', $.user_id, $.project_id)" }
            "SK" = { "S.$" = "States.Format('WORKSPACE#{}', $.workspace_id)" }
          }
          UpdateExpression     = "SET #run = :run, updatedAt = :now"
          ExpressionAttributeNames = {
            "#run" = "run"
          }
          ExpressionAttributeValues = {
            ":run" = {
              "M" = {
                "status"      = { "S" = "failed" }
                "output"      = { "S.$" = "$.result.output" }
                "error"       = { "S.$" = "$.result.error" }
                "completedAt" = { "S.$" = "$$.State.EnteredTime" }
              }
            }
            ":now" = { "S.$" = "$$.State.EnteredTime" }
          }
        }
        End = true
      }

      SetFailed = {
        Type     = "Task"
        Resource = "arn:aws:states:::dynamodb:updateItem"
        Parameters = {
          TableName = aws_dynamodb_table.openfactcheck.name
          Key = {
            "PK" = { "S.$" = "States.Format('USER#{}#PROJECT#{}', $.user_id, $.project_id)" }
            "SK" = { "S.$" = "States.Format('WORKSPACE#{}', $.workspace_id)" }
          }
          UpdateExpression     = "SET #run = :run, updatedAt = :now"
          ExpressionAttributeNames = {
            "#run" = "run"
          }
          ExpressionAttributeValues = {
            ":run" = {
              "M" = {
                "status"      = { "S" = "failed" }
                "output"      = { "S" = "" }
                "error"       = { "S" = "Engine execution failed — check Step Functions console for details" }
                "completedAt" = { "S.$" = "$$.State.EnteredTime" }
              }
            }
            ":now" = { "S.$" = "$$.State.EnteredTime" }
          }
        }
        End = true
      }
    }
  })

  tags = {
    Name = "OpenFactCheck - Pipeline - ${terraform.workspace} - ${var.aws_region}"
  }
}

# ##############################################################################
# IAM Role — Step Functions
# ##############################################################################

resource "aws_iam_role" "sfn_pipeline" {
  name = "openfactcheck-sfn-pipeline-${terraform.workspace}-${var.aws_region}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name = "OpenFactCheck - SFN Pipeline Role - ${terraform.workspace}"
  }
}

resource "aws_iam_role_policy" "sfn_pipeline_lambda" {
  name = "lambda-invoke"
  role = aws_iam_role.sfn_pipeline.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = [
          aws_lambda_function.engine.arn,
          "${aws_lambda_function.engine.arn}:*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "sfn_pipeline_dynamodb" {
  name = "dynamodb-update"
  role = aws_iam_role.sfn_pipeline.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "dynamodb:UpdateItem"
        Resource = aws_dynamodb_table.openfactcheck.arn
      }
    ]
  })
}
