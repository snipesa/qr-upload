#!/bin/bash
set -euo pipefail

ENVIRONMENT="${1:-dev}"
PROJECT_NAME="qr-upload"
STACK_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
S3_BUCKET="cf-templates--1tlzie64y9rw-us-east-1"
S3_PREFIX="qr-upload"
NESTED_DIR="nested"

if [ "$ENVIRONMENT" != "dev" ]; then
  echo "Only dev is supported right now."
  exit 1
fi

# Sync nested YAML files to S3
echo "Syncing nested templates to S3..."
aws s3 sync "$NESTED_DIR/" "s3://$S3_BUCKET/$S3_PREFIX/" \
  --exclude "*" \
  --include "*.yaml" \
  --include "*.yml" \
  --delete

echo "Nested templates synced successfully."

aws cloudformation deploy \
  --template-file qr-upload-stack.yaml \
  --stack-name "$STACK_NAME" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides Environment="$ENVIRONMENT" ProjectName="$PROJECT_NAME"

echo "Deployed stack: $STACK_NAME"
