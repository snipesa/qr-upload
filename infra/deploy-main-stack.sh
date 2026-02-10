#!/bin/bash
set -euo pipefail

# deploy-main-stack.sh - Deploy QR Upload main CloudFormation stack

usage() {
  echo "Usage: $0 -e <environment> [-p <profile>] [-d]"
  echo ""
  echo "Options:"
  echo "  -e, --environment     AWS environment to deploy to. Required."
  echo "                        Valid values: dev"
  echo "  -p, --profile         AWS CLI profile to use. Optional."
  echo "  -d, --debug           Enable debug mode (set -x). Optional."
  echo ""
  echo "Examples:"
  echo "  $0 -e dev"
  echo "  $0 -e dev -p my-aws-profile"
  echo "  $0 -e dev -d"
  exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    -e|--environment)
      AWS_ENV="$2"
      shift
      shift
      ;;
    -p|--profile)
      AWS_PROFILE="$2"
      shift
      shift
      ;;
    -d|--debug)
      DEBUG=true
      shift
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Unknown option: $1"
      usage
      ;;
  esac
done

# Enable debug mode if requested
if [ "${DEBUG:-false}" = true ]; then
  set -x
fi

# Validate required parameters
if [ -z "${AWS_ENV:-}" ]; then
  echo "ERROR: Environment (-e) must be specified"
  usage
fi

if [ "$AWS_ENV" != "dev" ]; then
  echo "ERROR: Only dev is supported right now."
  usage
fi

# Set AWS CLI profile if specified
if [ -n "${AWS_PROFILE:-}" ]; then
  AWS_PROFILE_PARAM="--profile $AWS_PROFILE"
else
  AWS_PROFILE_PARAM=""
fi

configure_environment() {
  PROJECT_NAME="qr-upload"
  STACK_NAME="${PROJECT_NAME}-${AWS_ENV}"
  S3_BUCKET="cf-templates--1tlzie64y9rw-us-east-1"
  S3_PREFIX="qr-upload"
  NESTED_DIR="nested"
  export AWS_REGION="us-east-1"

  DEPLOY_TS="$(date -u +%Y-%m-%d_%H%M%S)"
  DEPLOY_PREFIX="${S3_PREFIX}/${DEPLOY_TS}"
  DEPLOY_TEMPLATE="packaged-qr-upload-stack.yaml"

  echo "Configured for environment: $AWS_ENV"
  echo "Stack name: $STACK_NAME"
  echo "S3 bucket: $S3_BUCKET"
  echo "Deploy S3 prefix: $DEPLOY_PREFIX"
  echo "AWS Region: $AWS_REGION"
}

check_stack_exists() {
  echo "Checking if stack $STACK_NAME exists..."
  if aws $AWS_PROFILE_PARAM cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" &>/dev/null; then
    STACK_EXISTS=true
    echo "Stack $STACK_NAME exists, will update"
  else
    STACK_EXISTS=false
    echo "Stack $STACK_NAME does not exist, will create"
  fi
}

sync_nested_templates() {
  echo "Syncing nested templates to S3..."
  aws $AWS_PROFILE_PARAM s3 sync "$NESTED_DIR/" "s3://${S3_BUCKET}/${DEPLOY_PREFIX}/" \
    --exclude "*" \
    --include "*.yaml" \
    --include "*.yml" \
    --delete

  echo "Nested templates synced successfully."
}

prepare_deploy_template() {
  if [ -f "$DEPLOY_TEMPLATE" ]; then
    rm "$DEPLOY_TEMPLATE"
  fi

  echo "Preparing deployment template..."
  sed "s|/${S3_PREFIX}/|/${DEPLOY_PREFIX}/|g" qr-upload-stack.yaml > "$DEPLOY_TEMPLATE"

  if [ ! -f "$DEPLOY_TEMPLATE" ]; then
    echo "ERROR: Failed to create deployment template file"
    exit 1
  fi
}

deploy_stack() {
  echo "Deploying CloudFormation stack: $STACK_NAME"
  aws $AWS_PROFILE_PARAM cloudformation deploy \
    --template-file "$DEPLOY_TEMPLATE" \
    --stack-name "$STACK_NAME" \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides Environment="$AWS_ENV" ProjectName="$PROJECT_NAME" \
    --region "$AWS_REGION"

  echo "Deployment completed successfully"
}

show_outputs() {
  echo "Stack outputs:"
  aws $AWS_PROFILE_PARAM cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table \
    --region "$AWS_REGION"
}

cleanup() {
  echo "Cleaning up temporary files..."
  if [ -f "$DEPLOY_TEMPLATE" ]; then
    rm "$DEPLOY_TEMPLATE"
    echo "Removed $DEPLOY_TEMPLATE"
  fi
}

main() {
  configure_environment

  echo "Verifying AWS credentials..."
  aws $AWS_PROFILE_PARAM sts get-caller-identity --region "$AWS_REGION"

  check_stack_exists
  sync_nested_templates
  prepare_deploy_template
  deploy_stack
  show_outputs
  cleanup

  echo "Deployment for $AWS_ENV environment completed successfully!"
}

main
