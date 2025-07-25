provider "aws" {
  region = var.aws_region

  default_tags {
    tags = var.tags
  }
}

locals {
  function_name = "${var.service_name}-${var.environment}"
  table_name    = "${var.service_name}-scores-${var.environment}"
}

# DynamoDB Table
resource "aws_dynamodb_table" "leaderboard_scores" {
  name           = local.table_name
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "game_id"
  range_key      = "sort_key"

  attribute {
    name = "game_id"
    type = "S"
  }

  attribute {
    name = "sort_key"
    type = "S"
  }

  tags = {
    Name = local.table_name
  }
}

# Lambda execution role
resource "aws_iam_role" "lambda_role" {
  name = "${local.function_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Lambda execution policy
resource "aws_iam_policy" "lambda_policy" {
  name = "${local.function_name}-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = aws_dynamodb_table.leaderboard_scores.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# Package Lambda function
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "../src"
  output_path = "lambda_function.zip"
}

# Lambda function
resource "aws_lambda_function" "leaderboard_function" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = local.function_name
  role            = aws_iam_role.lambda_role.arn
  handler         = "leaderboard.handler.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime         = "python3.11"
  timeout         = 30

  environment {
    variables = {
      LEADERBOARD_TABLE = aws_dynamodb_table.leaderboard_scores.name
      POWERTOOLS_SERVICE_NAME = var.service_name
      POWERTOOLS_LOG_LEVEL = "INFO"
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_policy_attachment,
    aws_cloudwatch_log_group.lambda_logs,
  ]
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${local.function_name}"
  retention_in_days = 14
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "api_gateway_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.leaderboard_function.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.leaderboard_api.execution_arn}/*/*"
}

# API Gateway
resource "aws_api_gateway_rest_api" "leaderboard_api" {
  name        = "${local.function_name}-api"
  description = "Leaderboard service API"

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

# API Gateway deployment
resource "aws_api_gateway_deployment" "leaderboard_deployment" {
  depends_on = [
    aws_api_gateway_integration.lambda_integration,
    aws_api_gateway_integration.lambda_integration_proxy,
  ]

  rest_api_id = aws_api_gateway_rest_api.leaderboard_api.id
  stage_name  = var.environment

  lifecycle {
    create_before_destroy = true
  }
}

# Proxy resource
resource "aws_api_gateway_resource" "proxy" {
  rest_api_id = aws_api_gateway_rest_api.leaderboard_api.id
  parent_id   = aws_api_gateway_rest_api.leaderboard_api.root_resource_id
  path_part   = "{proxy+}"
}

# Proxy method
resource "aws_api_gateway_method" "proxy_method" {
  rest_api_id   = aws_api_gateway_rest_api.leaderboard_api.id
  resource_id   = aws_api_gateway_resource.proxy.id
  http_method   = "ANY"
  authorization = "NONE"
}

# Proxy integration
resource "aws_api_gateway_integration" "lambda_integration_proxy" {
  rest_api_id = aws_api_gateway_rest_api.leaderboard_api.id
  resource_id = aws_api_gateway_resource.proxy.id
  http_method = aws_api_gateway_method.proxy_method.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.leaderboard_function.invoke_arn
}

# Root method
resource "aws_api_gateway_method" "root_method" {
  rest_api_id   = aws_api_gateway_rest_api.leaderboard_api.id
  resource_id   = aws_api_gateway_rest_api.leaderboard_api.root_resource_id
  http_method   = "ANY"
  authorization = "NONE"
}

# Root integration
resource "aws_api_gateway_integration" "lambda_integration" {
  rest_api_id = aws_api_gateway_rest_api.leaderboard_api.id
  resource_id = aws_api_gateway_rest_api.leaderboard_api.root_resource_id
  http_method = aws_api_gateway_method.root_method.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.leaderboard_function.invoke_arn
}