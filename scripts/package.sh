#!/bin/bash
# Package Lambda function for deployment

set -e

echo "Packaging Lambda function..."

# Create temporary directory
TEMP_DIR=$(mktemp -d)
PACKAGE_DIR="$TEMP_DIR/package"

# Copy source code
cp -r src/* "$PACKAGE_DIR/"

# Install dependencies
pip install -r requirements.txt -t "$PACKAGE_DIR/" --no-deps

# Create deployment package
cd "$PACKAGE_DIR"
zip -r ../lambda_function.zip .
cd - > /dev/null

# Move package to current directory
mv "$TEMP_DIR/lambda_function.zip" ./

# Cleanup
rm -rf "$TEMP_DIR"

echo "Package created: lambda_function.zip"
echo "Size: $(du -h lambda_function.zip | cut -f1)"