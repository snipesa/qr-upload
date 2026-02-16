#!/bin/bash
set -euo pipefail

# Build and package WebSocket Event Handler Lambda function
echo "Building WebSocket Event Handler Lambda function..."

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
    python3 -m pip install -r requirements.txt -t "$BUILD_DIR/" --quiet
else
    echo "No dependencies to install (boto3 included in Lambda runtime)"
fi

# Create deployment package
echo "Creating deployment package..."
ZIP_BASENAME="websocket-event-handler"
ZIP_TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
ZIP_FILENAME="${ZIP_BASENAME}-${ZIP_TIMESTAMP}.zip"
cd "$BUILD_DIR"
zip -r "../${ZIP_FILENAME}" . -q
cd ..

# Upload to S3 and update SSM parameter
S3_BUCKET="cf-templates--1tlzie64y9rw-us-east-1"
S3_PREFIX="lambda-zip/websocket-event-handler"
SSM_PARAM_NAME="/qr-upload/websocket-event-handler/lambda-zip"

echo "Uploading ${ZIP_FILENAME} to s3://${S3_BUCKET}/${S3_PREFIX}/"
aws s3 cp "${ZIP_FILENAME}" "s3://${S3_BUCKET}/${S3_PREFIX}/${ZIP_FILENAME}"

echo "Updating SSM parameter ${SSM_PARAM_NAME}"
aws ssm put-parameter \
  --name "${SSM_PARAM_NAME}" \
  --type String \
  --value "${ZIP_FILENAME}" \
  --overwrite

# Clean up
rm -rf "$BUILD_DIR"

echo "✓ Deployment package created: ${ZIP_FILENAME}"
echo "Size: $(ls -lh "${ZIP_FILENAME}" | awk '{print $5}')"
rm -f "${ZIP_FILENAME}"
echo "Removed local package: ${ZIP_FILENAME}"
