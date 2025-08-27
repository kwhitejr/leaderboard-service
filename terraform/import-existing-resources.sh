#!/bin/bash
# Import existing AWS resources into Terraform state

# Navigate to terraform directory
cd "$(dirname "$0")"

# Import DynamoDB table
terraform import aws_dynamodb_table.leaderboard_scores leaderboard-scores-prod

# Import IAM role
terraform import aws_iam_role.lambda_role leaderboard-prod-role

# Import CloudWatch log group
terraform import aws_cloudwatch_log_group.lambda_logs /aws/lambda/leaderboard-prod

echo "Import complete. Run 'terraform plan' to verify state synchronization."