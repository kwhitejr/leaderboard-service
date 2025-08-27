#!/bin/bash
# Deploy infrastructure and Lambda function

set -e

ENVIRONMENT=${1:-dev}

echo "Deploying leaderboard service to $ENVIRONMENT environment..."

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "Error: AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

# Deploy infrastructure
echo "Deploying infrastructure..."
cd terraform/
terraform init
terraform plan -var="environment=$ENVIRONMENT"
terraform apply -var="environment=$ENVIRONMENT" -auto-approve
cd ..

echo "Deployment completed successfully!"
echo ""
echo "API Gateway URL:"
cd terraform/
terraform output api_gateway_url
cd ..

echo ""
echo "Test the deployment:"
echo "curl \$(terraform -chdir=terraform output -raw api_gateway_url)/health"