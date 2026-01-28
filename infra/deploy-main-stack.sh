#!/bin/bash
set -euo pipefail

ENVIRONMENT="${1:-dev}"
PROJECT_NAME="qr-upload"
STACK_NAME="${PROJECT_NAME}-${ENVIRONMENT}"

if [ "$ENVIRONMENT" != "dev" ]; then
  echo "Only dev is supported right now."
  exit 1
fi

aws cloudformation deploy \
  --template-file qr-upload-stack.yaml \
  --stack-name "$STACK_NAME" \
  --parameter-overrides Environment="$ENVIRONMENT" ProjectName="$PROJECT_NAME"

echo "Deployed stack: $STACK_NAME"
