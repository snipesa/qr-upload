# Infrastructure Specification

## Overview
CloudFormation template for deploying all AWS resources needed for the QR upload application.

## Resources Summary

### Core Services
1. **S3 Buckets** (2)
   - Website hosting bucket
   - Image upload bucket

2. **DynamoDB Table** (1)
   - Session state storage

3. **Lambda Functions** (2)
   - HTTP API handler
   - WebSocket/Event handler

4. **IAM Roles** (2)
   - HTTP API Lambda execution role
   - WebSocket/Event Lambda execution role

5. **CloudWatch Log Groups** (2)
   - HTTP API Lambda logs
   - WebSocket/Event Lambda logs

6. **API Gateway APIs** (2)
   - HTTP API (created manually - documented in CloudFormation)
   - WebSocket API (created manually - documented in CloudFormation)

---

## CloudFormation Structure

### Parameters

```yaml
Parameters:
  Environment:
    Type: String
    Default: dev
    AllowedValues: [dev, prod]
    Description: Environment name

  ProjectName:
    Type: String
    Default: qr-upload
    Description: Project name for resource naming

  LambdaDeploymentBucket:
    Type: String
    Description: S3 bucket containing Lambda deployment packages
```

---

## Resource Specifications

### 1. Website S3 Bucket

**Purpose**: Host static website files

**Properties**:
- **Bucket Name**: `{ProjectName}-website-{Environment}`
- **Website Configuration**:
  - Index Document: `index.html`
  - Error Document: `index.html`
- **Public Access**: Enabled (for website hosting)
- **CORS**: Configured for API calls

**CORS Configuration**:
```yaml
CorsConfiguration:
  CorsRules:
    - AllowedOrigins: ['*']
      AllowedMethods: [GET, HEAD]
      AllowedHeaders: ['*']
      MaxAge: 3600
```

**Bucket Policy**:
- Allow public read access: `s3:GetObject`

**Output**:
- Website URL: `http://{bucket}.s3-website-{region}.amazonaws.com`

---

### 2. Upload S3 Bucket

**Purpose**: Store user-uploaded images

**Properties**:
- **Bucket Name**: `{ProjectName}-uploads-{Environment}`
- **Public Access**: Blocked (private bucket)
- **Lifecycle Policy**: Delete objects after 30 days
- **CORS**: Configured for presigned URL uploads
- **Event Notification**: Trigger Lambda on object creation

**CORS Configuration**:
```yaml
CorsConfiguration:
  CorsRules:
    - AllowedOrigins: ['*']
      AllowedMethods: [PUT, POST]
      AllowedHeaders: ['*']
      MaxAge: 3600
```

**Event Notification**:
```yaml
NotificationConfiguration:
  LambdaConfigurations:
    - Event: s3:ObjectCreated:*
      Function: !GetAtt WebSocketEventLambda.Arn
      Filter:
        S3Key:
          Rules:
            - Name: prefix
              Value: session-uploads/
```

**Lifecycle Rule**:
```yaml
LifecycleConfiguration:
  Rules:
    - Id: DeleteOldUploads
      Status: Enabled
      ExpirationInDays: 30
```

---

### 3. DynamoDB Sessions Table

**Purpose**: Store upload session state

**Properties**:
- **Table Name**: `{ProjectName}-sessions-{Environment}`
- **Billing Mode**: PAY_PER_REQUEST (on-demand)
- **Primary Key**: `sessionId` (String)
- **TTL Attribute**: `expiresAt`
- **Streams**: Enabled (NEW_AND_OLD_IMAGES)

**Attribute Definitions**:
```yaml
AttributeDefinitions:
  - AttributeName: sessionId
    AttributeType: S
```

**Key Schema**:
```yaml
KeySchema:
  - AttributeName: sessionId
    KeyType: HASH
```

**TTL Configuration**:
```yaml
TimeToLiveSpecification:
  AttributeName: expiresAt
  Enabled: true
```

**Item Structure** (for reference):
```python
{
    'sessionId': 'uuid',           # Partition key
    'status': 'AWAITING_SCAN',     # Status enum
    'createdAt': 1234567890,       # Unix timestamp
    'expiresAt': 1234569690,       # Unix timestamp (TTL)
    'wsConnectionId': 'abc123',    # WebSocket connection ID
    'uploadKey': 's3/key/path'     # S3 object key
}
```

**Optional Enhancement** (for production):
- Add Global Secondary Index on `wsConnectionId` for faster lookups

---

### 4. HTTP API Lambda Function

**Properties**:
- **Function Name**: `{ProjectName}-http-api-{Environment}`
- **Runtime**: `python3.11`
- **Handler**: `lambda_function.lambda_handler`
- **Timeout**: 30 seconds
- **Memory**: 256 MB
- **Role**: HTTP API Lambda execution role

**Code**:
```yaml
Code:
  S3Bucket: !Ref LambdaDeploymentBucket
  S3Key: http_api_handler.zip
```

**Environment Variables**:
```yaml
Environment:
  Variables:
    SESSIONS_TABLE_NAME: !Ref SessionsTable
    UPLOAD_BUCKET_NAME: !Ref UploadBucket
```

**Layers**: None (boto3 included in runtime)

---

### 5. WebSocket/Event Lambda Function

**Properties**:
- **Function Name**: `{ProjectName}-websocket-event-{Environment}`
- **Runtime**: `python3.11`
- **Handler**: `lambda_function.lambda_handler`
- **Timeout**: 60 seconds
- **Memory**: 256 MB
- **Role**: WebSocket/Event Lambda execution role

**Code**:
```yaml
Code:
  S3Bucket: !Ref LambdaDeploymentBucket
  S3Key: websocket_event_handler.zip
```

**Environment Variables**:
```yaml
Environment:
  Variables:
    SESSIONS_TABLE_NAME: !Ref SessionsTable
    WS_API_ENDPOINT: !Sub '${WebSocketApi}.execute-api.${AWS::Region}.amazonaws.com/${Environment}'
```

**Event Source Mappings**:
- S3 bucket notification (configured in S3 bucket resource)

---

### 6. HTTP API Lambda IAM Role

**Purpose**: Execution role for HTTP API Lambda

**Managed Policies**:
- `AWSLambdaBasicExecutionRole` (CloudWatch Logs)

**Custom Policies**:

**DynamoDB Access**:
```yaml
PolicyName: DynamoDBAccess
Statement:
  - Effect: Allow
    Action:
      - dynamodb:GetItem
      - dynamodb:PutItem
      - dynamodb:UpdateItem
      - dynamodb:Query
    Resource: !GetAtt SessionsTable.Arn
```

**S3 Presigned URL Access**:
```yaml
PolicyName: S3PresignedUrlAccess
Statement:
  - Effect: Allow
    Action:
      - s3:PutObject
      - s3:PutObjectAcl
    Resource: !Sub '${UploadBucket.Arn}/*'
```

**Trust Relationship**:
```yaml
AssumeRolePolicyDocument:
  Version: '2012-10-17'
  Statement:
    - Effect: Allow
      Principal:
        Service: lambda.amazonaws.com
      Action: 'sts:AssumeRole'
```

---

### 7. WebSocket/Event Lambda IAM Role

**Purpose**: Execution role for WebSocket/Event Lambda

**Managed Policies**:
- `AWSLambdaBasicExecutionRole` (CloudWatch Logs)

**Custom Policies**:

**DynamoDB Access**:
```yaml
PolicyName: DynamoDBAccess
Statement:
  - Effect: Allow
    Action:
      - dynamodb:GetItem
      - dynamodb:PutItem
      - dynamodb:UpdateItem
      - dynamodb:Scan
    Resource: !GetAtt SessionsTable.Arn
```

**WebSocket Access**:
```yaml
PolicyName: WebSocketAccess
Statement:
  - Effect: Allow
    Action:
      - execute-api:ManageConnections
      - execute-api:Invoke
    Resource: '*'  # Can be scoped to specific API
```

**S3 Read Access**:
```yaml
PolicyName: S3ReadAccess
Statement:
  - Effect: Allow
    Action:
      - s3:GetObject
    Resource: !Sub '${UploadBucket.Arn}/*'
```

---

### 8. Lambda Invoke Permissions

**S3 to Lambda Permission**:
```yaml
Type: AWS::Lambda::Permission
Properties:
  FunctionName: !Ref WebSocketEventLambda
  Action: lambda:InvokeFunction
  Principal: s3.amazonaws.com
  SourceArn: !GetAtt UploadBucket.Arn
```

**API Gateway to Lambda Permissions** (for WebSocket):
```yaml
Type: AWS::Lambda::Permission
Properties:
  FunctionName: !Ref WebSocketEventLambda
  Action: lambda:InvokeFunction
  Principal: apigateway.amazonaws.com
  SourceArn: !Sub 'arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${WebSocketApi}/*'
```

---

### 9. CloudWatch Log Groups

**HTTP API Lambda Logs**:
```yaml
Type: AWS::Logs::LogGroup
Properties:
  LogGroupName: !Sub '/aws/lambda/${HttpApiLambda}'
  RetentionInDays: 7  # Adjust for production (14, 30, 90)
```

**WebSocket/Event Lambda Logs**:
```yaml
Type: AWS::Logs::LogGroup
Properties:
  LogGroupName: !Sub '/aws/lambda/${WebSocketEventLambda}'
  RetentionInDays: 7
```

---

### 10. API Gateway Resources (Placeholder)

**Note**: HTTP API and WebSocket API will be created manually via AWS Console.
The CloudFormation template includes placeholder resources for reference and outputs.

**WebSocket API** (placeholder for reference):
```yaml
WebSocketApi:
  Type: AWS::ApiGatewayV2::Api
  Properties:
    Name: !Sub '${ProjectName}-websocket-${Environment}'
    ProtocolType: WEBSOCKET
    RouteSelectionExpression: $request.body.action
```

**HTTP API** (to be created manually):
- See `docs/api-gateway-setup.md` for manual configuration
- Lambda functions will be integrated after manual creation

---

## Stack Outputs

### Website Outputs
```yaml
WebsiteBucketName:
  Description: Name of the S3 bucket for website hosting
  Value: !Ref WebsiteBucket
  Export:
    Name: !Sub '${AWS::StackName}-WebsiteBucket'

WebsiteURL:
  Description: URL of the website
  Value: !GetAtt WebsiteBucket.WebsiteURL
  Export:
    Name: !Sub '${AWS::StackName}-WebsiteURL'
```

### Storage Outputs
```yaml
UploadBucketName:
  Description: Name of the S3 bucket for uploads
  Value: !Ref UploadBucket
  Export:
    Name: !Sub '${AWS::StackName}-UploadBucket'

SessionsTableName:
  Description: Name of the DynamoDB sessions table
  Value: !Ref SessionsTable
  Export:
    Name: !Sub '${AWS::StackName}-SessionsTable'
```

### Lambda Outputs
```yaml
HttpApiLambdaArn:
  Description: ARN of the HTTP API Lambda function
  Value: !GetAtt HttpApiLambda.Arn
  Export:
    Name: !Sub '${AWS::StackName}-HttpApiLambdaArn'

WebSocketEventLambdaArn:
  Description: ARN of the WebSocket/Event Lambda function
  Value: !GetAtt WebSocketEventLambda.Arn
  Export:
    Name: !Sub '${AWS::StackName}-WebSocketEventLambdaArn'
```

### API Gateway Outputs
```yaml
WebSocketApiId:
  Description: WebSocket API ID (for manual integration)
  Value: !Ref WebSocketApi
  Export:
    Name: !Sub '${AWS::StackName}-WebSocketApiId'
```

---

## Parameter Files

### dev.json
```json
[
  {
    "ParameterKey": "Environment",
    "ParameterValue": "dev"
  },
  {
    "ParameterKey": "ProjectName",
    "ParameterValue": "qr-upload"
  },
  {
    "ParameterKey": "LambdaDeploymentBucket",
    "ParameterValue": "qr-upload-lambda-deployments-dev"
  }
]
```

### prod.json
```json
[
  {
    "ParameterKey": "Environment",
    "ParameterValue": "prod"
  },
  {
    "ParameterKey": "ProjectName",
    "ParameterValue": "qr-upload"
  },
  {
    "ParameterKey": "LambdaDeploymentBucket",
    "ParameterValue": "qr-upload-lambda-deployments-prod"
  }
]
```

---

## Deployment Process

### Prerequisites
1. Create Lambda deployment bucket manually:
   ```bash
   aws s3 mb s3://qr-upload-lambda-deployments-dev
   ```

2. Upload Lambda ZIP files:
   ```bash
   aws s3 cp http_api_handler.zip s3://qr-upload-lambda-deployments-dev/
   aws s3 cp websocket_event_handler.zip s3://qr-upload-lambda-deployments-dev/
   ```

### Deploy Stack
```bash
aws cloudformation deploy \
  --template-file cloudformation/main-stack.yaml \
  --stack-name qr-upload-dev \
  --parameter-overrides file://cloudformation/parameters/dev.json \
  --capabilities CAPABILITY_NAMED_IAM
```

### Verify Deployment
```bash
aws cloudformation describe-stacks \
  --stack-name qr-upload-dev \
  --query "Stacks[0].Outputs" \
  --output table
```

### Update Stack
- Same command as deployment
- CloudFormation will create a change set and apply updates

### Delete Stack
```bash
# Empty S3 buckets first
aws s3 rm s3://qr-upload-website-dev --recursive
aws s3 rm s3://qr-upload-uploads-dev --recursive

# Delete stack
aws cloudformation delete-stack --stack-name qr-upload-dev
```

---

## Cost Optimization

### S3
- Use lifecycle policies to delete old uploads
- Enable S3 Intelligent-Tiering for website assets (optional)

### Lambda
- Right-size memory allocation
- Use on-demand for low traffic
- Consider Provisioned Concurrency for production

### DynamoDB
- On-Demand pricing for variable workload
- Enable TTL to auto-delete expired sessions
- Consider Reserved Capacity for predictable workload

### CloudWatch
- Reduce log retention for non-production
- Use log sampling for high-volume events
- Set up log insights queries instead of exporting

### API Gateway
- HTTP API is cheaper than REST API
- WebSocket connections billed per minute
- Enable caching if needed (HTTP API)

---

## Monitoring & Alarms

### CloudWatch Alarms to Create

**Lambda Errors**:
```yaml
Type: AWS::CloudWatch::Alarm
Properties:
  AlarmName: !Sub '${ProjectName}-http-api-errors-${Environment}'
  MetricName: Errors
  Namespace: AWS/Lambda
  Statistic: Sum
  Period: 300
  EvaluationPeriods: 1
  Threshold: 5
  ComparisonOperator: GreaterThanThreshold
  Dimensions:
    - Name: FunctionName
      Value: !Ref HttpApiLambda
```

**Lambda Duration**:
```yaml
Type: AWS::CloudWatch::Alarm
Properties:
  AlarmName: !Sub '${ProjectName}-http-api-duration-${Environment}'
  MetricName: Duration
  Namespace: AWS/Lambda
  Statistic: Average
  Period: 300
  EvaluationPeriods: 2
  Threshold: 3000  # 3 seconds
  ComparisonOperator: GreaterThanThreshold
  Dimensions:
    - Name: FunctionName
      Value: !Ref HttpApiLambda
```

**DynamoDB Throttles**:
```yaml
Type: AWS::CloudWatch::Alarm
Properties:
  AlarmName: !Sub '${ProjectName}-dynamodb-throttles-${Environment}'
  MetricName: UserErrors
  Namespace: AWS/DynamoDB
  Statistic: Sum
  Period: 60
  EvaluationPeriods: 1
  Threshold: 1
  ComparisonOperator: GreaterThanThreshold
  Dimensions:
    - Name: TableName
      Value: !Ref SessionsTable
```

---

## Security Best Practices

### IAM
- Use least privilege principle
- Scope resource ARNs specifically
- Regular audit of permissions
- Use separate roles for different Lambdas

### S3
- Block public access on upload bucket
- Enable server-side encryption (SSE-S3)
- Use bucket policies, not ACLs
- Enable versioning for website bucket (optional)

### DynamoDB
- Enable point-in-time recovery (production)
- Encrypt at rest (enabled by default)
- Use IAM for access control
- Enable CloudTrail logging

### Lambda
- Use environment variables for configuration
- Never hardcode secrets
- Use VPC for sensitive workloads (if needed)
- Enable X-Ray tracing for debugging

### API Gateway
- Enable throttling
- Use API keys for additional security
- Consider AWS WAF for production
- Enable CloudWatch logging

---

## Disaster Recovery

### Backup Strategy
- **DynamoDB**: Enable point-in-time recovery
- **S3**: Enable versioning on upload bucket
- **Lambda**: Code stored in version control
- **CloudFormation**: Template in version control

### Recovery Steps
1. Redeploy CloudFormation stack
2. Restore DynamoDB table from backup
3. Redeploy Lambda functions
4. Recreate API Gateway configurations
5. Update website with new API endpoints

### RTO/RPO
- **RTO** (Recovery Time Objective): 1-2 hours
- **RPO** (Recovery Point Objective): 5-15 minutes (DynamoDB)

---

## Multi-Environment Strategy

### Naming Convention
- Format: `{ProjectName}-{ResourceType}-{Environment}`
- Example: `qr-upload-website-dev`, `qr-upload-uploads-prod`

### Environment Differences

**Dev**:
- Lower log retention (7 days)
- Smaller Lambda memory
- No reserved capacity
- Lifecycle: 30 days

**Prod**:
- Higher log retention (30-90 days)
- Optimized Lambda memory
- Consider reserved capacity
- Lifecycle: 90 days
- Enable DynamoDB backups
- Add CloudWatch alarms
- Enable AWS WAF

### Deployment Order
1. Deploy to dev
2. Test thoroughly
3. Deploy to prod
4. Monitor closely

---

## Troubleshooting

### Stack Fails to Create
- Check IAM permissions
- Verify Lambda deployment bucket exists
- Check parameter values
- Review CloudFormation events

### Lambda Not Triggered by S3
- Verify S3 event notification configuration
- Check Lambda permissions
- Review S3 bucket policy
- Check S3 key prefix filter

### DynamoDB Access Denied
- Verify IAM role permissions
- Check resource ARNs
- Review trust relationships
- Check table name in environment variables

### WebSocket Connection Fails
- Verify Lambda environment variable `WS_API_ENDPOINT`
- Check IAM permissions for `execute-api:ManageConnections`
- Review WebSocket API configuration
- Check connection ID validity
