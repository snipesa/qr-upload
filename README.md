# QR Upload Deploy Commands

## Infrastructure Deployment

### 1. Deploy Main Infrastructure (S3, DynamoDB, IAM Roles)
```bash
cd infra
./deploy-main-stack.sh -e dev
```

### 2. Deploy Website to S3
```bash
aws s3 sync website/ s3://qr-upload-website-dev --delete
```
