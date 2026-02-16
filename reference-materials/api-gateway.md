# API Gateway Configuration Guide

## Overview

This document provides step-by-step instructions for manually creating and configuring the HTTP API and WebSocket API in AWS API Gateway console. These APIs integrate with the Lambda functions deployed via CloudFormation.

---

## Prerequisites

Before setting up API Gateway, ensure:
- [x] CloudFormation stack deployed with Lambda functions
- [x] Lambda function ARNs available
- [x] DynamoDB sessions table created
- [x] You have necessary IAM permissions to create API Gateway resources

---

## HTTP API Configuration

### Purpose
Handles synchronous request-response operations:
- Create upload sessions
- Generate presigned S3 upload URLs

### Step 1: Create HTTP API

1. Navigate to **API Gateway** in AWS Console
2. Click **Create API**
3. Select **HTTP API** → Click **Build**
4. Configure API:
   - **API name**: `qr-upload-http-api-{environment}` (e.g., `qr-upload-http-api-dev`)
   - **Description**: `HTTP API for QR upload session management`
   - Skip **Add integrations** for now (we'll add them per route)
5. Click **Next**
6. Configure routes (skip for now, we'll create them next)
7. Configure stages:
   - **Stage name**: `production` (or `$default`)
   - **Auto-deploy**: Enabled
8. Click **Next** → **Create**

### Step 2: Create Lambda Integration

Since both routes use the same Lambda function (with internal routing), we only need **one integration**:

1. In the API details page, click **Integrations** in left sidebar
2. Click **Create**
3. Configure integration:
   - **Integration type**: Lambda function
   - **Integration target**: Select `qr-upload-http-api-{environment}` Lambda
   - **Integration name**: `http-api-lambda-integration`
   - **Payload format version**: `2.0` (default for HTTP API)
4. Click **Create**
5. Grant API Gateway permission to invoke Lambda:
   - Permission should be added automatically
   - If not, use AWS CLI:
   ```bash
   aws lambda add-permission \
     --function-name qr-upload-http-api-dev \
     --statement-id apigateway-http-invoke \
     --action lambda:InvokeFunction \
     --principal apigateway.amazonaws.com \
     --source-arn "arn:aws:execute-api:{region}:{account-id}:{api-id}/*/*"
   ```

### Step 3: Create Routes

#### Route 1: POST /sessions

1. Click **Routes** in left sidebar
2. Click **Create**
3. Configure route:
   - **Method**: `POST`
   - **Path**: `/sessions`
4. Click **Create**
5. Attach integration:
   - Click on the newly created route
   - Under **Integration**, select `http-api-lambda-integration`
   - Click **Attach integration**

#### Route 2: GET /upload-url

1. Click **Create** under Routes
2. Configure route:
   - **Method**: `GET`
   - **Path**: `/upload-url`
3. Click **Create**
4. Attach integration:
   - Click on the route
   - Under **Integration**, select `http-api-lambda-integration`
   - Click **Attach integration**

### Step 4: Configure CORS

1. Click **CORS** in left sidebar
2. Click **Configure**
3. Configure CORS settings:
   - **Access-Control-Allow-Origin**: `*` (or specific domain for production)
   - **Access-Control-Allow-Methods**: `GET, POST, OPTIONS`
   - **Access-Control-Allow-Headers**: `Content-Type, Authorization`
   - **Access-Control-Max-Age**: `3600` (1 hour)
4. Click **Save**

### Step 5: Get API Endpoint

1. Click **Stages** in left sidebar
2. Click on your stage (e.g., `production` or `$default`)
3. Copy the **Invoke URL**: `https://{api-id}.execute-api.{region}.amazonaws.com`
4. This is your HTTP API base URL for the website configuration

### HTTP API Endpoint Summary

| Method | Path | Purpose | Lambda Handler |
|--------|------|---------|----------------|
| POST | `/sessions` | Create new upload session | `create_session.handle()` |
| GET | `/upload-url?sessionId={id}` | Get presigned S3 upload URL | `generate_presigned_url.handle()` |

### Example HTTP API Requests

#### Create Session
```bash
curl -X POST https://{api-id}.execute-api.{region}.amazonaws.com/sessions

# Response:
# {
#   "sessionId": "550e8400-e29b-41d4-a716-446655440000",
#   "expiresAt": 1706400000
# }
```

#### Get Presigned URL
```bash
curl -X GET "https://{api-id}.execute-api.{region}.amazonaws.com/upload-url?sessionId=550e8400-e29b-41d4-a716-446655440000"

# Response:
# {
#   "uploadUrl": "https://bucket.s3.amazonaws.com/session-uploads/abc123/image.jpg?X-Amz-..."
# }
```

---

## WebSocket API Configuration

### Purpose
Provides persistent connection for server-to-client real-time notifications:
- Notify web app when image upload completes
- Maintain connection state during upload process

### Step 1: Create WebSocket API

1. Navigate to **API Gateway** in AWS Console
2. Click **Create API**
3. Select **WebSocket API** → Click **Build**
4. Configure API:
   - **API name**: `qr-upload-websocket-api-{environment}`
   - **Description**: `WebSocket API for real-time upload notifications`
   - **Route selection expression**: `$request.body.action` (default)
5. Click **Next**

### Step 2: Add Predefined Routes

WebSocket APIs require three predefined routes:

#### Route 1: $connect

1. On **Add routes** page, enter route key: `$connect`
2. Click **Add $connect**
3. Configure integration (next step)

#### Route 2: $disconnect

1. Enter route key: `$disconnect`
2. Click **Add $disconnect**
3. Configure integration (next step)

#### Route 3: $default (Optional)

1. Enter route key: `$default`
2. Click **Add $default**
3. This catches any unhandled messages (optional for this project)

### Step 3: Configure Route Integrations

After creating the API, configure integrations for each route:

#### $connect Integration

1. Click on **$connect** route in the routes list
2. Under **Integration Request**, click **Edit**
3. Configure:
   - **Integration type**: Lambda function
   - **Lambda function**: Select `qr-upload-websocket-event-{environment}`
   - **Integration timeout**: Default (29 seconds)
4. Click **Save**
5. Grant permission:
   ```bash
   aws lambda add-permission \
     --function-name qr-upload-websocket-event-dev \
     --statement-id apigateway-ws-connect \
     --action lambda:InvokeFunction \
     --principal apigateway.amazonaws.com \
     --source-arn "arn:aws:execute-api:{region}:{account-id}:{api-id}/*/$connect"
   ```

#### $disconnect Integration

1. Click on **$disconnect** route
2. Under **Integration Request**, click **Edit**
3. Configure:
   - **Integration type**: Lambda function
   - **Lambda function**: Select `qr-upload-websocket-event-{environment}` (same function)
4. Click **Save**
5. Grant permission:
   ```bash
   aws lambda add-permission \
     --function-name qr-upload-websocket-event-dev \
     --statement-id apigateway-ws-disconnect \
     --action lambda:InvokeFunction \
     --principal apigateway.amazonaws.com \
     --source-arn "arn:aws:execute-api:{region}:{account-id}:{api-id}/*/$disconnect"
   ```

### Step 4: Deploy WebSocket API

1. Click **Stages** in left sidebar
2. Click **Create**
3. Configure stage:
   - **Stage name**: `production`
   - **Description**: `Production stage for WebSocket API`
4. Click **Deploy**

### Step 5: Get WebSocket Endpoint

1. In **Stages** → `production`
2. Copy the **WebSocket URL**: `wss://{api-id}.execute-api.{region}.amazonaws.com/production`
3. This is your WebSocket API URL for the website configuration

### Step 6: Update CloudFormation Stack with WebSocket Endpoint

The WebSocket event handler Lambda needs the API Gateway endpoint to send messages. Update the CloudFormation stack:

**Option 1: Update via AWS Console**
1. Navigate to **CloudFormation** in AWS Console
2. Select the `qr-upload-dev` stack
3. Click **Update** → **Use current template** → **Next**
4. Update the parameter:
   - **WsApiEndpoint**: `{api-id}.execute-api.{region}.amazonaws.com/production`
   - Example: `r0k1fs92k5.execute-api.us-east-1.amazonaws.com/production`
5. Click through **Next** → **Submit**

**Option 2: Update via deployment script**
```bash
cd infra
# Edit deploy-main-stack.sh to accept parameter overrides, or update the parameter default in qr-upload-stack.yaml
```

**Important Notes**:
- The endpoint format is `{api-id}.execute-api.{region}.amazonaws.com/production` (no `https://` or `wss://` prefix, **no trailing slash**)
- The Lambda code constructs the full `https://` URL internally: `https://r0k1fs92k5.execute-api.us-east-1.amazonaws.com/production`
- This is required for the Lambda to send WebSocket messages to connected clients

**About the @connections URL:**
- Your WebSocket URL: `wss://r0k1fs92k5.execute-api.us-east-1.amazonaws.com/production/`
- The Management API endpoint: `https://r0k1fs92k5.execute-api.us-east-1.amazonaws.com/production/@connections`
- The boto3 SDK automatically appends `/@connections` when calling `post_to_connection()`, so you only provide: `r0k1fs92k5.execute-api.us-east-1.amazonaws.com/production`

### WebSocket API Routes Summary

| Route | Purpose | Lambda Handler | Response |
|-------|---------|----------------|----------|
| `$connect` | Client connects, validates sessionId | `websocket_connect.handle()` | 200 (success) or 401 (unauthorized) |
| `$disconnect` | Client disconnects, cleanup | `websocket_disconnect.handle()` | 200 |
| `$default` | Catch-all for unhandled messages | (optional) | - |

### WebSocket Connection Flow

```
1. Web app creates session (HTTP API)
   ↓
2. Web app opens WebSocket: wss://{api-id}...?sessionId={id}
   ↓
3. API Gateway invokes Lambda with $connect route
   ↓
4. Lambda validates sessionId, stores connectionId in DynamoDB
   ↓
5. Connection established (or rejected with 401)
   ↓
6. User scans QR and uploads image to S3
   ↓
7. S3 event triggers Lambda
   ↓
8. Lambda retrieves connectionId from session
   ↓
9. Lambda sends message via API Gateway Management API
   ↓
10. Web app receives message and updates UI
```

### Example WebSocket Connection (JavaScript)

```javascript
const sessionId = '550e8400-e29b-41d4-a716-446655440000';
const wsUrl = 'wss://{api-id}.execute-api.{region}.amazonaws.com/production';

const ws = new WebSocket(`${wsUrl}?sessionId=${sessionId}`);

ws.onopen = () => {
    console.log('WebSocket connected');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received message:', data);
    
    if (data.type === 'upload_complete') {
        console.log('Image uploaded:', data.imageUrl);
        // Update UI to show success
    }
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};

ws.onclose = () => {
    console.log('WebSocket closed');
};
```

### WebSocket Message Format

When an image is uploaded to S3, the Lambda function sends this message to the connected client:

```json
{
    "type": "upload_complete",
    "sessionId": "550e8400-e29b-41d4-a716-446655440000",
    "imageUrl": "https://qr-upload-uploads-dev.s3.amazonaws.com/session-uploads/abc123/image.jpg",
    "uploadedAt": 1706400000
}
```

---

## Testing API Gateway

### Test HTTP API

#### Using curl

```bash
# Test session creation
curl -X POST https://{api-id}.execute-api.{region}.amazonaws.com/sessions

# Test presigned URL (replace sessionId with actual value from above)
curl -X GET "https://{api-id}.execute-api.{region}.amazonaws.com/upload-url?sessionId={sessionId}"
```

#### Using Postman

1. Create new request
2. Set method to POST
3. URL: `https://{api-id}.execute-api.{region}.amazonaws.com/sessions`
4. Send request
5. Verify 200 response with sessionId
6. Create GET request for `/upload-url` with sessionId query parameter

### Test WebSocket API

#### Using wscat (CLI tool)

```bash
# Install wscat
npm install -g wscat

# Connect (replace sessionId with actual value)
wscat -c "wss://{api-id}.execute-api.{region}.amazonaws.com/production?sessionId={sessionId}"

# You should see "Connected" if sessionId is valid
# Keep connection open and upload an image to S3 (use presigned URL from HTTP API)
# You should receive a message when upload completes
```

#### Using Browser Console

```javascript
const ws = new WebSocket('wss://{api-id}.execute-api.{region}.amazonaws.com/production?sessionId={sessionId}');

ws.onopen = () => console.log('Connected');
ws.onmessage = (e) => console.log('Message:', e.data);
ws.onerror = (e) => console.error('Error:', e);
ws.onclose = () => console.log('Closed');
```

### End-to-End Test

1. **Create session**: POST to HTTP API `/sessions`
2. **Get presigned URL**: GET from HTTP API `/upload-url?sessionId={id}`
3. **Connect WebSocket**: Open connection with sessionId query parameter
4. **Upload image**: Use presigned URL to upload an image:
   ```bash
   curl -X PUT "{presignedUrl}" \
     --upload-file image.jpg \
     -H "Content-Type: image/jpeg"
   ```
5. **Verify notification**: Check WebSocket receives `upload_complete` message
6. **Verify storage**: Check S3 bucket for uploaded image at `session-uploads/{sessionId}/image.jpg`

---

## Monitoring & Debugging

### CloudWatch Logs

Both Lambda functions log to CloudWatch. Check logs for:

**HTTP API Lambda** (`/aws/lambda/qr-upload-http-api-{env}`):
- Session creation requests
- Presigned URL generation
- DynamoDB operations
- Errors and exceptions

**WebSocket Event Lambda** (`/aws/lambda/qr-upload-websocket-event-{env}`):
- WebSocket connection events
- S3 upload completion events
- Message sending operations
- Connection errors (e.g., GoneException)

### Common Issues & Solutions

#### Issue: CORS errors in browser
**Solution**: Verify CORS configuration in HTTP API includes:
- `Access-Control-Allow-Origin: *`
- `Access-Control-Allow-Methods: GET, POST, OPTIONS`
- `Access-Control-Allow-Headers: Content-Type`

#### Issue: WebSocket connection fails with 403
**Solution**: 
- Verify sessionId query parameter is included
- Check sessionId exists in DynamoDB
- Check session not expired
- Review Lambda logs for authorization errors

#### Issue: WebSocket message not received after upload
**Solution**:
- Verify S3 event notification is configured on upload bucket
- Check Lambda has permission to be invoked by S3
- Verify Lambda environment variable `WEBSOCKET_API_ENDPOINT` is correct
- Check Lambda logs for errors during message sending
- Verify connectionId is stored in session

#### Issue: Presigned URL expired
**Solution**:
- Presigned URLs expire after 15 minutes by default
- Regenerate URL by calling `/upload-url` endpoint again
- Consider increasing expiration time in Lambda code if needed

#### Issue: Lambda not triggered by S3 upload
**Solution**:
- Verify S3 event notification configuration has correct prefix filter
- Check Lambda resource policy allows S3 invocation
- Verify object is uploaded to correct path: `session-uploads/{sessionId}/image.jpg`

---

## API Gateway Outputs for CloudFormation

Although API Gateway is created manually, document the outputs for reference:

### HTTP API Outputs
- **API ID**: `{api-id}`
- **Invoke URL**: `https://{api-id}.execute-api.{region}.amazonaws.com`
- **Stage**: `production` or `$default`

### WebSocket API Outputs
- **API ID**: `{api-id}`
- **WebSocket URL**: `wss://{api-id}.execute-api.{region}.amazonaws.com/production`
- **Management API Endpoint** (for WS_API_ENDPOINT): `{api-id}.execute-api.{region}.amazonaws.com/production`

### Add to Website Configuration

Update `website/js/app.js` or `website/config.js` with these values:

```javascript
const CONFIG = {
    httpApiUrl: 'https://{http-api-id}.execute-api.{region}.amazonaws.com',
    wsApiUrl: 'wss://{ws-api-id}.execute-api.{region}.amazonaws.com/production'
};
```

---

## Security Considerations

### HTTP API
- Use CORS to restrict origins in production
- Consider adding API key or AWS IAM authorization for production
- Rate limiting via AWS WAF (optional)

### WebSocket API
- Session validation on $connect prevents unauthorized connections
- connectionId is opaque and not guessable
- Sessions expire after 1 hour (via DynamoDB TTL)
- Consider adding additional authentication for production

### Best Practices
- Use HTTPS/WSS only (default for API Gateway)
- Enable CloudWatch logging for audit trail
- Use least-privilege IAM permissions
- Implement rate limiting for production
- Validate all input in Lambda functions
- Don't expose sensitive data in error messages

---

## Cost Optimization

### HTTP API
- Pay per request: $1.00 per million requests
- First 1 million requests per month are free (12 months)

### WebSocket API
- Connection minutes: $0.25 per million connection minutes
- Messages: $1.00 per million messages
- Disconnect after upload to minimize connection time

### Optimization Tips
- Use caching for frequent requests (if applicable)
- Set appropriate Lambda timeout and memory
- Use DynamoDB on-demand pricing for variable workload
- Enable S3 lifecycle policy to delete old uploads
- Monitor costs with AWS Cost Explorer

---

## Next Steps

After configuring API Gateway:

1. [ ] Copy API endpoint URLs
2. [ ] Update Lambda environment variables (WebSocket endpoint)
3. [ ] Update website configuration with API URLs
4. [ ] Test each endpoint individually
5. [ ] Run end-to-end test
6. [ ] Deploy website to S3
7. [ ] Test from actual mobile device
8. [ ] Set up CloudWatch alarms (optional)
9. [ ] Document any custom modifications

---

## Reference Links

- [AWS API Gateway HTTP API Documentation](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html)
- [AWS API Gateway WebSocket API Documentation](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api.html)
- [Lambda Integration with API Gateway](https://docs.aws.amazon.com/lambda/latest/dg/services-apigateway.html)
- [API Gateway Management API (for WebSocket)](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-how-to-call-websocket-api-connections.html)
