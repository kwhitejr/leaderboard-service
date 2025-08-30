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
  name         = local.table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "game_id"
  range_key    = "sort_key"

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

# Create deployment package directory
resource "null_resource" "lambda_package" {
  triggers = {
    requirements = filemd5("../requirements.txt")
    source_code  = filemd5("../src/leaderboard/handler.py")
    models       = filemd5("../src/leaderboard/models.py")
    database     = filemd5("../src/leaderboard/database.py")
    # Force recreation to fix architecture compatibility
    platform_fix = "docker_build_v1"
  }

  provisioner "local-exec" {
    command = <<-EOT
      rm -rf lambda_package
      mkdir -p lambda_package
      cp -r ../src/* lambda_package/
      if command -v docker > /dev/null; then
        # Use Docker to ensure proper Linux x86_64 packages
        docker run --rm -v "$PWD/../requirements.txt:/requirements.txt" -v "$PWD/lambda_package:/lambda_package" python:3.11-slim bash -c "
          pip install -r /requirements.txt -t /lambda_package/
        "
      else
        # Fallback to local pip install
        pip install -r ../requirements.txt -t lambda_package/
      fi
      find lambda_package -name "*.pyc" -delete
      find lambda_package -name "__pycache__" -type d -exec rm -rf {} +
    EOT
  }

  # Clean up after deployment
  provisioner "local-exec" {
    when    = destroy
    command = "rm -rf lambda_package lambda_function.zip"
  }
}

# Package Lambda function with dependencies
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "lambda_package"
  output_path = "lambda_function.zip"

  depends_on = [null_resource.lambda_package]
}

# Lambda function
resource "aws_lambda_function" "leaderboard_function" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = local.function_name
  role             = aws_iam_role.lambda_role.arn
  handler          = "leaderboard.handler.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 30

  environment {
    variables = {
      LEADERBOARD_TABLE       = aws_dynamodb_table.leaderboard_scores.name
      POWERTOOLS_SERVICE_NAME = var.service_name
      POWERTOOLS_LOG_LEVEL    = "INFO"
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

  lifecycle {
    create_before_destroy = true
  }
}

# API Gateway stage
resource "aws_api_gateway_stage" "leaderboard_stage" {
  deployment_id = aws_api_gateway_deployment.leaderboard_deployment.id
  rest_api_id   = aws_api_gateway_rest_api.leaderboard_api.id
  stage_name    = var.environment
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
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.leaderboard_function.invoke_arn
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
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.leaderboard_function.invoke_arn
}

# Route53 Zone (assuming it already exists)
data "aws_route53_zone" "main" {
  name         = "kwhitejr.com"
  private_zone = false
}

# SSL Certificate for API domain (regional)
resource "aws_acm_certificate" "api_cert" {
  provider          = aws
  domain_name       = var.api_domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = var.tags
}

# Certificate validation
resource "aws_route53_record" "api_cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.api_cert.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.main.zone_id
}

resource "aws_acm_certificate_validation" "api_cert_validation" {
  certificate_arn         = aws_acm_certificate.api_cert.arn
  validation_record_fqdns = [for record in aws_route53_record.api_cert_validation : record.fqdn]

  timeouts {
    create = "5m"
  }
}

# API Gateway Custom Domain
resource "aws_api_gateway_domain_name" "api_domain" {
  domain_name              = var.api_domain_name
  regional_certificate_arn = aws_acm_certificate_validation.api_cert_validation.certificate_arn

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = var.tags
}

# API Gateway Base Path Mapping
resource "aws_api_gateway_base_path_mapping" "api_mapping" {
  api_id      = aws_api_gateway_rest_api.leaderboard_api.id
  stage_name  = aws_api_gateway_stage.leaderboard_stage.stage_name
  domain_name = aws_api_gateway_domain_name.api_domain.domain_name
}

# Route53 A record for API domain
resource "aws_route53_record" "api_domain" {
  name    = aws_api_gateway_domain_name.api_domain.domain_name
  type    = "A"
  zone_id = data.aws_route53_zone.main.zone_id

  alias {
    evaluate_target_health = true
    name                   = aws_api_gateway_domain_name.api_domain.regional_domain_name
    zone_id                = aws_api_gateway_domain_name.api_domain.regional_zone_id
  }
}