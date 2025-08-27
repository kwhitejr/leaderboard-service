#!/bin/bash
# Setup script for Terraform remote state backend

set -e

echo "Setting up Terraform remote state backend..."

# Check if AWS credentials are configured
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo "Error: AWS credentials not configured."
    echo "Please run: aws configure"
    echo "Or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables"
    exit 1
fi

# Step 1: Comment out the backend configuration temporarily
echo "1. Temporarily disabling remote backend for initial setup..."
sed -i 's/^  backend "s3"/  #backend "s3"/' versions.tf
sed -i 's/^    bucket/#    bucket/' versions.tf
sed -i 's/^    key/#    key/' versions.tf
sed -i 's/^    region/#    region/' versions.tf
sed -i 's/^    dynamodb_table/#    dynamodb_table/' versions.tf
sed -i 's/^    encrypt/#    encrypt/' versions.tf
sed -i 's/^  }/#  }/' versions.tf

# Step 2: Create backend infrastructure with local state
echo "2. Creating S3 bucket and DynamoDB table for remote state..."
terraform init
terraform apply -target=aws_s3_bucket.terraform_state -target=aws_s3_bucket_versioning.terraform_state_versioning -target=aws_s3_bucket_encryption.terraform_state_encryption -target=aws_s3_bucket_public_access_block.terraform_state -target=aws_dynamodb_table.terraform_locks -auto-approve

# Step 3: Re-enable the backend configuration
echo "3. Re-enabling remote backend configuration..."
sed -i 's/^  #backend "s3"/  backend "s3"/' versions.tf
sed -i 's/^#    bucket/    bucket/' versions.tf
sed -i 's/^#    key/    key/' versions.tf
sed -i 's/^#    region/    region/' versions.tf
sed -i 's/^#    dynamodb_table/    dynamodb_table/' versions.tf
sed -i 's/^#    encrypt/    encrypt/' versions.tf
sed -i 's/^#  }/  }/' versions.tf

# Step 2: Migrate to remote state
echo "2. Migrating to remote state backend..."
terraform init -migrate-state

# Step 3: Import existing resources
echo "3. Importing existing AWS resources..."
terraform import aws_dynamodb_table.leaderboard_scores leaderboard-scores-prod || echo "DynamoDB table already imported or doesn't exist"
terraform import aws_iam_role.lambda_role leaderboard-prod-role || echo "IAM role already imported or doesn't exist"  
terraform import aws_cloudwatch_log_group.lambda_logs /aws/lambda/leaderboard-prod || echo "CloudWatch log group already imported or doesn't exist"

# Step 4: Verify state
echo "4. Verifying Terraform state..."
terraform plan

echo "Remote state backend setup complete!"
echo "Your pipeline can now use the remote state for consistent deployments."