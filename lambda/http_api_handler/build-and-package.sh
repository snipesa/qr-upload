#!/bin/bash
set -euo pipefail

# Build and package HTTP API Lambda function
echo "Building HTTP API Lambda function..."

# Create temp build directory
BUILD_DIR="build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Copy Lambda code
echo "Copying Lambda code..."
cp -r __init__.py lambda_function.py handlers utils "$BUILD_DIR/"

# Check if requirements.txt has dependencies
if grep -v "^#" requirements.txt | grep -v "^$" > /dev/null 2>&1; then
    echo "Installing dependencies..."
    pip install -r requirements.txt -t "$BUILD_DIR/" --quiet
else
    echo "No dependencies to install (boto3 included in Lambda runtime)"
fi

# Create deployment package
echo "Creating deployment package..."
cd "$BUILD_DIR"
zip -r ../http-api-handler.zip . -q
cd ..

# Clean up
rm -rf "$BUILD_DIR"

echo "✓ Deployment package created: http-api-handler.zip"
echo "Size: $(ls -lh http-api-handler.zip | awk '{print $5}')"
