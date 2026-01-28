# QR Upload Application - Development Guide

## Project Overview

A serverless QR-based image upload application built on AWS. Users scan a QR code to upload images from their phone directly to S3, with real-time WebSocket notifications to the web app.

## Architecture

- **Frontend**: Static website hosted on S3
- **Backend**: AWS Lambda functions (Python 3.12)
- **Storage**: S3 buckets (website hosting + image uploads)
- **Database**: DynamoDB for session management
- **APIs**: API Gateway (HTTP + WebSocket)
- **Infrastructure**: CloudFormation

## Reference Documentation

- [Project Description](./project-description.md) - Complete system overview and user flow
- [Infrastructure Specification](./infrastructure-specification.md) - CloudFormation resources and configuration
- [Lambda Specification](./lambda-specification.md) - Lambda function implementation details
- [Website Specification](./website-specification.md) - Frontend implementation details
- [API Gateway Configuration](./api-gateway.md) - API Gateway setup and integration

---

## User Stories

### Epic 1: Infrastructure Setup

#### Story 1.1: Create S3 Website Hosting Bucket
**As a** DevOps engineer  
**I want** an S3 bucket configured for static website hosting  
**So that** users can access the web application

**Acceptance Criteria:**
- [ ] Bucket name: `qr-upload-website-{environment}`
- [ ] Static website hosting enabled
- [ ] Index document: `index.html`
- [ ] Error document: `index.html`
- [ ] Public read access enabled via bucket policy
- [ ] CORS configured for API calls
- [ ] CloudFormation template created in `infra/cloudformation/template.yaml`
- [ ] Outputs include website URL

**Documentation:**
See [infrastructure-specification.md](./infrastructure-specification.md) - Section 1: Website S3 Bucket

**Technical Notes:**
- Use `AWS::S3::Bucket` resource
- Include `WebsiteConfiguration` property
- Add `PublicAccessBlockConfiguration` with appropriate settings
- CORS: Allow GET, HEAD methods from any origin

---

#### Story 1.2: Create S3 Upload Bucket
**As a** DevOps engineer  
**I want** an S3 bucket to store user-uploaded images  
**So that** images can be uploaded directly from phones using presigned URLs

**Acceptance Criteria:**
- [ ] Bucket name: `qr-upload-uploads-{environment}`
- [ ] Public access blocked (private bucket)
- [ ] CORS configured for presigned URL uploads (PUT method)
- [ ] Lifecycle policy: Delete objects after 30 days
- [ ] Event notification configured to trigger Lambda on object creation
- [ ] CloudFormation template updated
- [ ] Prefix pattern: `session-uploads/{sessionId}/`

**Documentation:**
See [infrastructure-specification.md](./infrastructure-specification.md) - Section 2: Upload S3 Bucket

**Technical Notes:**
- Event notification filter: `session-uploads/` prefix
- CORS: Allow PUT, POST methods with required headers
- Use `AWS::S3::BucketNotification` or inline configuration
- Lambda permission required for S3 invocation

---

#### Story 1.3: Create DynamoDB Sessions Table
**As a** backend developer  
**I want** a DynamoDB table to store upload session state  
**So that** the system can track session lifecycle and WebSocket connections

**Acceptance Criteria:**
- [ ] Table name: `qr-upload-sessions-{environment}`
- [ ] Primary key: `sessionId` (String)
- [ ] Attributes: `connectionId`, `status`, `uploadUrl`, `createdAt`, `expiresAt`
- [ ] TTL enabled on `expiresAt` attribute (1-hour expiration)
- [ ] Billing mode: PAY_PER_REQUEST
- [ ] CloudFormation template updated
- [ ] Global Secondary Index (optional): `connectionId` for WebSocket lookups

**Documentation:**
See [infrastructure-specification.md](./infrastructure-specification.md) - Section 3: DynamoDB Table

**Technical Notes:**
- TTL calculation: `current_timestamp + 3600` seconds
- Status values: `created`, `waiting_upload`, `completed`, `error`
- Use `AWS::DynamoDB::Table` resource
- Consider GSI if WebSocket disconnect needs reverse lookup

---

#### Story 1.4: Create IAM Roles for Lambda Functions
**As a** DevOps engineer  
**I want** IAM roles with least-privilege permissions for Lambda functions  
**So that** functions have only the permissions they need

**Acceptance Criteria:**
- [ ] HTTP API Lambda role with permissions:
  - `dynamodb:GetItem`, `PutItem`, `UpdateItem` on sessions table
  - `s3:PutObject` on upload bucket (for presigned URL generation)
  - CloudWatch Logs write access
- [ ] WebSocket/Event Lambda role with permissions:
  - `dynamodb:GetItem`, `UpdateItem`, `Query` on sessions table
  - `execute-api:ManageConnections` for WebSocket API
  - CloudWatch Logs write access
- [ ] Roles follow naming convention: `qr-upload-{function-type}-role-{environment}`
- [ ] CloudFormation template updated

**Documentation:**
See [infrastructure-specification.md](./infrastructure-specification.md) - Section 4: IAM Roles

**Technical Notes:**
- Use `AWS::IAM::Role` with `AssumeRolePolicyDocument` for Lambda
- Attach inline policies or managed policies
- Use `!GetAtt` to reference resource ARNs

---

#### Story 1.5: Create CloudFormation Deployment Script
**As a** DevOps engineer  
**I want** a shell script to deploy the CloudFormation stack  
**So that** infrastructure can be deployed consistently across environments

**Acceptance Criteria:**
- [ ] Script: `infra/cloudformation/deploy-stack.sh`
- [ ] Accepts environment parameter (dev/prod)
- [ ] Creates/updates CloudFormation stack
- [ ] Validates template before deployment
- [ ] Displays stack outputs after deployment
- [ ] Error handling for failed deployments
- [ ] Usage: `./deploy-stack.sh dev`

**Technical Notes:**
```bash
#!/bin/bash
ENVIRONMENT=$1
STACK_NAME="qr-upload-stack-${ENVIRONMENT}"
aws cloudformation deploy \
  --template-file template.yaml \
  --stack-name $STACK_NAME \
  --parameter-overrides Environment=$ENVIRONMENT \
  --capabilities CAPABILITY_IAM
```

---

### Epic 2: Lambda Functions - HTTP API Handler

#### Story 2.1: Setup Lambda Project Structure
**As a** backend developer  
**I want** a well-organized Python project structure for Lambda functions  
**So that** code is maintainable and testable

**Acceptance Criteria:**
- [ ] Directory structure created as per lambda-specification.md
- [ ] `requirements.txt` with boto3 dependency
- [ ] `__init__.py` files in all packages
- [ ] `shared/` module for common utilities
- [ ] Separate handlers for each endpoint
- [ ] Build script to create deployment ZIP: `build-lambda.sh`

**Documentation:**
See [lambda-specification.md](./lambda-specification.md) - File Structure

**File Structure:**
```
lambda/
├── requirements.txt
├── build-lambda.sh
├── http_api_handler/
│   ├── __init__.py
│   ├── lambda_function.py
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── create_session.py
│   │   └── generate_presigned_url.py
│   └── utils/
│       ├── __init__.py
│       ├── dynamodb.py
│       └── response.py
├── websocket_event_handler/
│   ├── __init__.py
│   ├── lambda_function.py
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── websocket_connect.py
│   │   ├── websocket_disconnect.py
│   │   └── s3_upload_completion.py
│   └── utils/
│       ├── __init__.py
│       ├── dynamodb.py
│       ├── websocket.py
│       └── response.py
└── shared/
    ├── __init__.py
    ├── constants.py
    └── validators.py
```

---

#### Story 2.2: Implement HTTP API Lambda Entry Point
**As a** backend developer  
**I want** a Lambda handler that routes HTTP requests  
**So that** different endpoints can be handled by separate modules

**Acceptance Criteria:**
- [ ] File: `lambda/http_api_handler/lambda_function.py`
- [ ] Function: `lambda_handler(event, context)`
- [ ] Routes POST `/sessions` to `create_session.handle()`
- [ ] Routes GET `/upload-url` to `generate_presigned_url.handle()`
- [ ] Returns 404 for unknown routes
- [ ] Uses Python logging module (not print)
- [ ] Handles exceptions and returns proper error responses
- [ ] Logs request details for debugging

**Documentation:**
See [lambda-specification.md](./lambda-specification.md) - Lambda 1: HTTP API Handler

**Technical Notes:**
```python
import logging
from handlers import create_session, generate_presigned_url
from utils.response import error_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info(f"Received event: {event}")
    
    http_method = event['requestContext']['http']['method']
    path = event['requestContext']['http']['path']
    
    try:
        if http_method == 'POST' and path == '/sessions':
            return create_session.handle(event)
        elif http_method == 'GET' and path == '/upload-url':
            return generate_presigned_url.handle(event)
        else:
            return error_response('Not Found', 404)
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        return error_response('Internal Server Error', 500)
```

---

#### Story 2.3: Implement Create Session Handler
**As a** backend developer  
**I want** an endpoint to create upload sessions  
**So that** the web app can generate unique QR codes for each upload

**Acceptance Criteria:**
- [ ] File: `lambda/http_api_handler/handlers/create_session.py`
- [ ] Function: `handle(event)` returns session data
- [ ] Generates unique sessionId (UUID)
- [ ] Calculates expiration timestamp (1 hour from creation)
- [ ] Creates DynamoDB item with session metadata
- [ ] Returns JSON response with sessionId
- [ ] Handles DynamoDB errors gracefully
- [ ] Logs session creation

**Documentation:**
See [lambda-specification.md](./lambda-specification.md) - Handler: create_session.py

**Response Format:**
```json
{
    "sessionId": "550e8400-e29b-41d4-a716-446655440000",
    "expiresAt": 1706400000
}
```

**Technical Notes:**
- Use `uuid.uuid4()` for sessionId
- Use `int(time.time()) + 3600` for expiresAt
- Session status: `created`
- Store in DynamoDB: sessionId, status, createdAt, expiresAt

---

#### Story 2.4: Implement Generate Presigned URL Handler
**As a** backend developer  
**I want** an endpoint to generate S3 presigned upload URLs  
**So that** phones can upload images directly to S3

**Acceptance Criteria:**
- [ ] File: `lambda/http_api_handler/handlers/generate_presigned_url.py`
- [ ] Function: `handle(event)` returns presigned URL
- [ ] Validates sessionId query parameter
- [ ] Verifies session exists in DynamoDB
- [ ] Checks session not expired
- [ ] Generates presigned URL with S3 key: `session-uploads/{sessionId}/image.jpg`
- [ ] URL expires in 15 minutes
- [ ] Updates session status to `waiting_upload`
- [ ] Returns JSON response with uploadUrl
- [ ] Returns 400 for invalid/expired sessions

**Documentation:**
See [lambda-specification.md](./lambda-specification.md) - Handler: generate_presigned_url.py

**Response Format:**
```json
{
    "uploadUrl": "https://bucket.s3.amazonaws.com/session-uploads/abc123/image.jpg?X-Amz-..."
}
```

**Technical Notes:**
- Use `boto3.client('s3').generate_presigned_url()`
- Method: `put_object`
- ExpiresIn: 900 seconds (15 minutes)
- Content-Type: Allow multiple image types

---

#### Story 2.5: Implement DynamoDB Utility Module
**As a** backend developer  
**I want** a reusable DynamoDB utility module  
**So that** database operations are consistent and DRY

**Acceptance Criteria:**
- [ ] File: `lambda/http_api_handler/utils/dynamodb.py`
- [ ] Function: `get_session(session_id)` returns session or None
- [ ] Function: `create_session(session_data)` creates new session
- [ ] Function: `update_session(session_id, updates)` updates session attributes
- [ ] Uses boto3 DynamoDB resource or client
- [ ] Handles `ClientError` exceptions
- [ ] Logs database operations
- [ ] Reads table name from environment variable

**Documentation:**
See [lambda-specification.md](./lambda-specification.md) - utils/dynamodb.py

**Technical Notes:**
```python
import os
import boto3
import logging

logger = logging.getLogger()
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['SESSIONS_TABLE_NAME'])

def get_session(session_id):
    response = table.get_item(Key={'sessionId': session_id})
    return response.get('Item')
```

---

#### Story 2.6: Implement Response Utility Module
**As a** backend developer  
**I want** a response utility module for consistent API responses  
**So that** all endpoints return properly formatted HTTP responses

**Acceptance Criteria:**
- [ ] File: `lambda/http_api_handler/utils/response.py`
- [ ] Function: `success_response(data, status_code=200)` returns formatted response
- [ ] Function: `error_response(message, status_code)` returns error response
- [ ] Includes proper headers (Content-Type, CORS)
- [ ] JSON serialization of response body
- [ ] CORS headers: `Access-Control-Allow-Origin: *`

**Technical Notes:**
```python
import json

def success_response(data, status_code=200):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(data)
    }

def error_response(message, status_code):
    return success_response({'error': message}, status_code)
```

---

#### Story 2.7: Create HTTP API Lambda Deployment Package
**As a** DevOps engineer  
**I want** a script to build and package the HTTP API Lambda  
**So that** it can be deployed to AWS

**Acceptance Criteria:**
- [ ] Script: `lambda/build-lambda.sh`
- [ ] Accepts function name parameter: `http_api_handler` or `websocket_event_handler`
- [ ] Installs dependencies from requirements.txt
- [ ] Creates ZIP file with code and dependencies
- [ ] Output: `dist/{function-name}.zip`
- [ ] Excludes unnecessary files (tests, .pyc, __pycache__)
- [ ] Creates dist/ directory if not exists

**Technical Notes:**
```bash
#!/bin/bash
FUNCTION_NAME=$1
BUILD_DIR="build/${FUNCTION_NAME}"
DIST_DIR="dist"

rm -rf $BUILD_DIR
mkdir -p $BUILD_DIR $DIST_DIR

# Install dependencies
pip install -r requirements.txt -t $BUILD_DIR

# Copy function code
cp -r $FUNCTION_NAME/* $BUILD_DIR/
cp -r shared $BUILD_DIR/

# Create ZIP
cd $BUILD_DIR
zip -r ../../$DIST_DIR/${FUNCTION_NAME}.zip . -x "*.pyc" "*__pycache__*"
cd ../..

echo "Package created: $DIST_DIR/${FUNCTION_NAME}.zip"
```

---

#### Story 2.8: Deploy HTTP API Lambda Function
**As a** DevOps engineer  
**I want** the HTTP API Lambda function deployed to AWS  
**So that** the API can handle session creation and presigned URL requests

**Acceptance Criteria:**
- [ ] Lambda function created via CloudFormation
- [ ] Function name: `qr-upload-http-api-{environment}`
- [ ] Runtime: Python 3.12
- [ ] Handler: `lambda_function.lambda_handler`
- [ ] Timeout: 30 seconds
- [ ] Memory: 256 MB
- [ ] Environment variables set: `SESSIONS_TABLE_NAME`, `UPLOAD_BUCKET_NAME`
- [ ] IAM role attached from Story 1.4
- [ ] Deployment package uploaded from Story 2.7
- [ ] CloudWatch log group created

**Documentation:**
See [infrastructure-specification.md](./infrastructure-specification.md) - Section 5: Lambda Functions

**Technical Notes:**
- Use `AWS::Lambda::Function` resource
- Code: Reference S3 bucket and key for ZIP file
- Or use local deployment with `aws lambda update-function-code`

---

### Epic 3: Lambda Functions - WebSocket & Event Handler

#### Story 3.1: Implement WebSocket Event Handler Entry Point
**As a** backend developer  
**I want** a Lambda handler that processes WebSocket lifecycle events and S3 events  
**So that** connections can be managed and upload notifications sent

**Acceptance Criteria:**
- [ ] File: `lambda/websocket_event_handler/lambda_function.py`
- [ ] Function: `lambda_handler(event, context)`
- [ ] Detects event type: WebSocket or S3
- [ ] Routes WebSocket `$connect` to `websocket_connect.handle()`
- [ ] Routes WebSocket `$disconnect` to `websocket_disconnect.handle()`
- [ ] Routes S3 `ObjectCreated` to `s3_upload_completion.handle()`
- [ ] Handles exceptions and logs errors
- [ ] Returns appropriate responses for each event type

**Documentation:**
See [lambda-specification.md](./lambda-specification.md) - Lambda 2: WebSocket Event Handler

**Technical Notes:**
```python
import logging
from handlers import websocket_connect, websocket_disconnect, s3_upload_completion

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info(f"Received event: {event}")
    
    # Detect event source
    if 'requestContext' in event and 'eventType' in event['requestContext']:
        # WebSocket event
        route_key = event['requestContext']['routeKey']
        if route_key == '$connect':
            return websocket_connect.handle(event)
        elif route_key == '$disconnect':
            return websocket_disconnect.handle(event)
    elif 'Records' in event and event['Records'][0]['eventSource'] == 'aws:s3':
        # S3 event
        return s3_upload_completion.handle(event)
    
    return {'statusCode': 400, 'body': 'Unknown event type'}
```

---

#### Story 3.2: Implement WebSocket Connect Handler
**As a** backend developer  
**I want** to handle WebSocket connection events  
**So that** the web app can receive real-time notifications

**Acceptance Criteria:**
- [ ] File: `lambda/websocket_event_handler/handlers/websocket_connect.py`
- [ ] Function: `handle(event)` processes connection
- [ ] Extracts connectionId from event
- [ ] Extracts sessionId from query string parameters
- [ ] Validates sessionId exists in DynamoDB
- [ ] Updates session with connectionId
- [ ] Returns 200 on success, 401 on invalid session
- [ ] Logs connection establishment

**Documentation:**
See [lambda-specification.md](./lambda-specification.md) - Handler: websocket_connect.py

**Technical Notes:**
- connectionId: `event['requestContext']['connectionId']`
- sessionId: `event['queryStringParameters']['sessionId']`
- Update DynamoDB: Add connectionId to session
- Authorization: Return 401 if session invalid/expired

---

#### Story 3.3: Implement WebSocket Disconnect Handler
**As a** backend developer  
**I want** to handle WebSocket disconnection events  
**So that** connection state is cleaned up properly

**Acceptance Criteria:**
- [ ] File: `lambda/websocket_event_handler/handlers/websocket_disconnect.py`
- [ ] Function: `handle(event)` processes disconnection
- [ ] Extracts connectionId from event
- [ ] Optionally updates session status or removes connectionId
- [ ] Returns 200 response
- [ ] Logs disconnection

**Documentation:**
See [lambda-specification.md](./lambda-specification.md) - Handler: websocket_disconnect.py

**Technical Notes:**
- connectionId: `event['requestContext']['connectionId']`
- Optional: Query DynamoDB by connectionId (requires GSI)
- Graceful handling: Connection may already be expired

---

#### Story 3.4: Implement S3 Upload Completion Handler
**As a** backend developer  
**I want** to handle S3 upload completion events  
**So that** the web app is notified when an image is uploaded

**Acceptance Criteria:**
- [ ] File: `lambda/websocket_event_handler/handlers/s3_upload_completion.py`
- [ ] Function: `handle(event)` processes S3 event
- [ ] Extracts bucket name and object key from event
- [ ] Parses sessionId from object key (e.g., `session-uploads/{sessionId}/image.jpg`)
- [ ] Retrieves session from DynamoDB
- [ ] Gets connectionId from session
- [ ] Sends WebSocket message to connection with upload details
- [ ] Updates session status to `completed`
- [ ] Handles errors (connection closed, session not found)

**Documentation:**
See [lambda-specification.md](./lambda-specification.md) - Handler: s3_upload_completion.py

**WebSocket Message Format:**
```json
{
    "type": "upload_complete",
    "sessionId": "550e8400-e29b-41d4-a716-446655440000",
    "imageUrl": "https://bucket.s3.amazonaws.com/session-uploads/abc123/image.jpg",
    "uploadedAt": 1706400000
}
```

**Technical Notes:**
- Parse key: `event['Records'][0]['s3']['object']['key']`
- Use `utils.websocket.send_message(connection_id, message)`
- Handle `GoneException` if connection closed

---

#### Story 3.5: Implement WebSocket Utility Module
**As a** backend developer  
**I want** a WebSocket utility module for sending messages  
**So that** WebSocket operations are reusable

**Acceptance Criteria:**
- [ ] File: `lambda/websocket_event_handler/utils/websocket.py`
- [ ] Function: `send_message(connection_id, message)` sends message to WebSocket client
- [ ] Uses boto3 API Gateway Management API client
- [ ] Reads WebSocket API endpoint from environment variable
- [ ] Handles `GoneException` (client disconnected)
- [ ] Logs message sending operations

**Documentation:**
See [lambda-specification.md](./lambda-specification.md) - utils/websocket.py

**Technical Notes:**
```python
import os
import boto3
import json
import logging

logger = logging.getLogger()
apigateway_client = boto3.client('apigatewaymanagementapi',
    endpoint_url=os.environ['WEBSOCKET_API_ENDPOINT'])

def send_message(connection_id, message):
    try:
        apigateway_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message).encode('utf-8')
        )
        logger.info(f"Message sent to connection {connection_id}")
    except apigateway_client.exceptions.GoneException:
        logger.warning(f"Connection {connection_id} is gone")
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        raise
```

---

#### Story 3.6: Implement WebSocket Handler DynamoDB Utility
**As a** backend developer  
**I want** DynamoDB utilities for the WebSocket handler  
**So that** session operations are consistent

**Acceptance Criteria:**
- [ ] File: `lambda/websocket_event_handler/utils/dynamodb.py`
- [ ] Function: `get_session(session_id)` retrieves session
- [ ] Function: `update_session_connection(session_id, connection_id)` adds connection to session
- [ ] Function: `update_session_status(session_id, status)` updates session status
- [ ] Function: `query_by_connection_id(connection_id)` (optional, requires GSI)
- [ ] Handles DynamoDB exceptions
- [ ] Logs operations

**Technical Notes:**
- Similar to HTTP handler's DynamoDB utility but with additional methods
- Consider code sharing via `shared/` module if significant overlap

---

#### Story 3.7: Deploy WebSocket Event Handler Lambda
**As a** DevOps engineer  
**I want** the WebSocket/Event Lambda function deployed to AWS  
**So that** WebSocket lifecycle and S3 events can be handled

**Acceptance Criteria:**
- [ ] Lambda function created via CloudFormation
- [ ] Function name: `qr-upload-websocket-event-{environment}`
- [ ] Runtime: Python 3.12
- [ ] Handler: `lambda_function.lambda_handler`
- [ ] Timeout: 60 seconds
- [ ] Memory: 256 MB
- [ ] Environment variables set: `SESSIONS_TABLE_NAME`, `WEBSOCKET_API_ENDPOINT`
- [ ] IAM role attached from Story 1.4
- [ ] Triggered by S3 bucket notification (ObjectCreated events)
- [ ] Integrated with WebSocket API routes (manual setup)
- [ ] CloudWatch log group created

**Documentation:**
See [infrastructure-specification.md](./infrastructure-specification.md) - Section 5: Lambda Functions

**Technical Notes:**
- S3 event source: Configured in S3 bucket resource
- WebSocket integration: Configured manually in API Gateway (see Story 4.x)
- Environment variable for WebSocket endpoint: `https://{api-id}.execute-api.{region}.amazonaws.com/production`

---

### Epic 4: API Gateway Configuration

#### Story 4.1: Document HTTP API Configuration
**As a** DevOps engineer  
**I want** documentation for creating the HTTP API in API Gateway  
**So that** the API can be set up manually in the console

**Acceptance Criteria:**
- [ ] Documentation file: `reference-materials/api-gateway.md`
- [ ] HTTP API section with step-by-step console instructions
- [ ] Endpoint definitions: POST `/sessions`, GET `/upload-url`
- [ ] Lambda integration configuration for each route
- [ ] CORS configuration
- [ ] Stage deployment (e.g., `production`)
- [ ] API URL format and example

**Documentation:**
See [api-gateway.md](./api-gateway.md) - HTTP API Configuration

---

#### Story 4.2: Document WebSocket API Configuration
**As a** DevOps engineer  
**I want** documentation for creating the WebSocket API in API Gateway  
**So that** real-time notifications can be sent to the web app

**Acceptance Criteria:**
- [ ] Documentation file updated: `reference-materials/api-gateway.md`
- [ ] WebSocket API section with console instructions
- [ ] Route definitions: `$connect`, `$disconnect`, `$default` (optional)
- [ ] Lambda integration for each route
- [ ] Authorization configuration (query parameter: sessionId)
- [ ] Stage deployment (e.g., `production`)
- [ ] WebSocket URL format and example
- [ ] Connection lifecycle explanation

**Documentation:**
See [api-gateway.md](./api-gateway.md) - WebSocket API Configuration

---

#### Story 4.3: Test API Gateway Integration
**As a** QA engineer  
**I want** to test all API Gateway endpoints  
**So that** integrations with Lambda functions work correctly

**Acceptance Criteria:**
- [ ] Test POST `/sessions` - returns sessionId
- [ ] Test GET `/upload-url?sessionId=...` - returns presigned URL
- [ ] Test WebSocket connection with sessionId query parameter
- [ ] Test WebSocket receives message after S3 upload
- [ ] Test error cases: invalid sessionId, expired session
- [ ] Document test procedures and expected responses
- [ ] Create example curl commands or Postman collection

**Technical Notes:**
- Use curl for HTTP API testing
- Use wscat or browser WebSocket client for WebSocket testing
- Validate CORS headers in responses

---

### Epic 5: Website Development

#### Story 5.1: Create HTML Structure
**As a** frontend developer  
**I want** the main HTML file with all UI elements  
**So that** users can interact with the upload flow

**Acceptance Criteria:**
- [ ] File: `website/index.html`
- [ ] Includes QRCode.js library from CDN
- [ ] Multiple view states: initial, QR, loading, success, error
- [ ] Buttons: Start Upload, Cancel, Retry, New Upload
- [ ] Container for QR code display
- [ ] Message display areas
- [ ] Proper semantic HTML structure
- [ ] Meta tags for responsive design

**Documentation:**
See [website-specification.md](./website-specification.md) - index.html

**View States:**
- `#initial-view` - Upload button and info message
- `#qr-view` - QR code and scanning instructions
- `#loading-view` - Spinner during transitions
- `#success-view` - Upload complete message
- `#error-view` - Error message with retry option

---

#### Story 5.2: Create CSS Styling
**As a** frontend developer  
**I want** attractive and responsive styling  
**So that** the app looks professional on all devices

**Acceptance Criteria:**
- [ ] File: `website/css/styles.css`
- [ ] Gradient background (purple theme)
- [ ] Card-based layout with shadows
- [ ] Responsive design (mobile-first)
- [ ] Button hover effects
- [ ] Loading spinner animation
- [ ] Success/error color states
- [ ] View transition animations
- [ ] QR code container styling

**Documentation:**
See [website-specification.md](./website-specification.md) - styles.css

**Color Scheme:**
- Primary gradient: #667eea to #764ba2
- Success: #4caf50
- Error: #f44336
- Background: White cards on gradient

---

#### Story 5.3: Implement Main Application Logic
**As a** frontend developer  
**I want** JavaScript to handle the upload workflow  
**So that** users can create sessions, display QR codes, and receive notifications

**Acceptance Criteria:**
- [ ] File: `website/js/app.js`
- [ ] Class: `QRUploadApp`
- [ ] Configuration: HTTP API URL, WebSocket API URL
- [ ] Method: `init()` - Initialize app
- [ ] Method: `displayRandomMessage()` - Show random info message
- [ ] Method: `startUpload()` - Begin upload flow
- [ ] Method: `createSession()` - Call HTTP API
- [ ] Method: `connectWebSocket(sessionId)` - Open WebSocket connection
- [ ] Method: `handleWebSocketMessage(data)` - Process notifications
- [ ] Method: `showView(viewName)` - Switch between views
- [ ] Method: `cancelUpload()` - Cancel and reset
- [ ] Error handling for all async operations

**Documentation:**
See [website-specification.md](./website-specification.md) - app.js

**Info Messages (examples):**
- "Did you know? QR codes can hold up to 4,296 alphanumeric characters!"
- "Fun fact: QR stands for 'Quick Response'"
- "Tip: Make sure your camera has good lighting when scanning"

---

#### Story 5.4: Implement QR Code Generation
**As a** frontend developer  
**I want** to generate QR codes from upload URLs  
**So that** users can scan them with their phones

**Acceptance Criteria:**
- [ ] File: `website/js/qr-generator.js`
- [ ] Function: `generateQRCode(url, containerId)` generates QR code
- [ ] Uses QRCode.js library
- [ ] QR code size: 256x256 pixels
- [ ] Error correction level: M (medium)
- [ ] Clears existing QR code before generating new one
- [ ] Handles errors gracefully

**Documentation:**
See [website-specification.md](./website-specification.md) - qr-generator.js

**Technical Notes:**
```javascript
function generateQRCode(url, containerId) {
    const container = document.getElementById(containerId);
    container.innerHTML = ''; // Clear existing
    
    new QRCode(container, {
        text: url,
        width: 256,
        height: 256,
        correctLevel: QRCode.CorrectLevel.M
    });
}
```

---

#### Story 5.5: Implement WebSocket Client
**As a** frontend developer  
**I want** a WebSocket client to receive real-time notifications  
**So that** the web app updates when upload completes

**Acceptance Criteria:**
- [ ] File: `website/js/websocket-client.js`
- [ ] Class: `WebSocketClient`
- [ ] Method: `connect(sessionId)` - Establishes WebSocket connection
- [ ] Method: `disconnect()` - Closes connection
- [ ] Method: `onMessage(callback)` - Registers message handler
- [ ] Handles connection errors and retries
- [ ] Sends sessionId as query parameter
- [ ] Logs connection status

**Documentation:**
See [website-specification.md](./website-specification.md) - websocket-client.js

**Technical Notes:**
```javascript
class WebSocketClient {
    connect(wsUrl, sessionId) {
        this.ws = new WebSocket(`${wsUrl}?sessionId=${sessionId}`);
        this.ws.onopen = () => console.log('WebSocket connected');
        this.ws.onmessage = (event) => this.messageCallback(JSON.parse(event.data));
        this.ws.onerror = (error) => console.error('WebSocket error:', error);
        this.ws.onclose = () => console.log('WebSocket closed');
    }
}
```

---

#### Story 5.6: Deploy Website to S3
**As a** DevOps engineer  
**I want** to upload website files to the S3 hosting bucket  
**So that** the application is accessible via the web

**Acceptance Criteria:**
- [ ] Script: `website/deploy-website.sh`
- [ ] Accepts environment parameter (dev/prod)
- [ ] Syncs all website files to S3 bucket
- [ ] Sets proper content types for files
- [ ] Invalidates CloudFront cache (if using CloudFront)
- [ ] Displays website URL after deployment
- [ ] Usage: `./deploy-website.sh dev`

**Technical Notes:**
```bash
#!/bin/bash
ENVIRONMENT=$1
BUCKET_NAME="qr-upload-website-${ENVIRONMENT}"

aws s3 sync . s3://$BUCKET_NAME/ \
  --exclude "*.sh" \
  --exclude "README.md" \
  --delete

echo "Website deployed to: http://${BUCKET_NAME}.s3-website-$(aws configure get region).amazonaws.com"
```

---

#### Story 5.7: Update Website Configuration with API URLs
**As a** frontend developer  
**I want** to configure the website with correct API endpoints  
**So that** it can communicate with the backend

**Acceptance Criteria:**
- [ ] Configuration method in `app.js` or separate config file
- [ ] HTTP API URL from CloudFormation/API Gateway outputs
- [ ] WebSocket API URL from CloudFormation/API Gateway outputs
- [ ] Environment-specific configuration (dev/prod)
- [ ] Consider using `config.js` file or environment variables

**Technical Notes:**
```javascript
// Option 1: config.js file
const CONFIG = {
    httpApiUrl: 'https://abc123.execute-api.us-east-1.amazonaws.com',
    wsApiUrl: 'wss://xyz789.execute-api.us-east-1.amazonaws.com/production'
};

// Option 2: Fetch from a JSON file
fetch('/config.json')
    .then(response => response.json())
    .then(config => new QRUploadApp(config));
```

---

### Epic 6: Testing & Validation

#### Story 6.1: Create End-to-End Test Procedure
**As a** QA engineer  
**I want** documented test procedures for the entire flow  
**So that** the system can be validated after deployment

**Acceptance Criteria:**
- [ ] Test document: `reference-materials/testing.md`
- [ ] Step-by-step manual test procedures
- [ ] Expected results for each step
- [ ] Test scenarios: happy path, error cases, edge cases
- [ ] Screenshots or video of successful flow
- [ ] Performance benchmarks (if applicable)

**Test Scenarios:**
1. Happy path: Create session → Scan QR → Upload image → Receive notification
2. Expired session: Try to upload after 1 hour
3. Invalid session: Use wrong sessionId
4. Network error handling
5. Multiple simultaneous uploads
6. Mobile device compatibility

---

#### Story 6.2: Test Lambda Functions Locally
**As a** backend developer  
**I want** to test Lambda functions locally  
**So that** I can verify logic before deploying

**Acceptance Criteria:**
- [ ] Test scripts for each Lambda handler
- [ ] Mock AWS services (DynamoDB, S3, API Gateway)
- [ ] Unit tests for utility functions
- [ ] Use `pytest` framework
- [ ] Test coverage > 80%
- [ ] Document how to run tests

**Technical Notes:**
- Use `moto` library to mock AWS services
- Use `unittest.mock` for other dependencies
- Test file structure: `lambda/tests/`

---

#### Story 6.3: Monitor and Debug with CloudWatch
**As a** DevOps engineer  
**I want** to set up CloudWatch monitoring and alarms  
**So that** issues can be detected and debugged quickly

**Acceptance Criteria:**
- [ ] CloudWatch log groups for both Lambda functions
- [ ] Structured logging with proper log levels
- [ ] CloudWatch alarms for errors (optional)
- [ ] Dashboard with key metrics (optional)
- [ ] Document how to view logs and troubleshoot

**Key Metrics:**
- Lambda invocation count
- Lambda error rate
- Lambda duration
- DynamoDB read/write capacity
- S3 upload count

---

### Epic 7: Documentation & Deployment

#### Story 7.1: Create Root README with Deployment Commands
**As a** DevOps engineer  
**I want** a README file with all deployment commands  
**So that** the project can be deployed easily

**Acceptance Criteria:**
- [ ] File: `README.md` (root level)
- [ ] Project overview and architecture diagram
- [ ] Prerequisites (AWS CLI, Python, etc.)
- [ ] Deployment commands for each component
- [ ] Configuration instructions
- [ ] Testing instructions
- [ ] Troubleshooting section

**Deployment Commands Section:**
```markdown
## Deployment Commands

### 1. Deploy CloudFormation Stack
```bash
cd infra/cloudformation
./deploy-stack.sh dev
```

### 2. Build Lambda Functions
```bash
cd lambda
./build-lambda.sh http_api_handler
./build-lambda.sh websocket_event_handler
```

### 3. Deploy Website
```bash
cd website
./deploy-website.sh dev
```

### 4. Configure API Gateway
Follow instructions in [reference-materials/api-gateway.md](./reference-materials/api-gateway.md)
```

---

#### Story 7.2: Update Development.md with Progress
**As a** project manager  
**I want** development.md to track completed stories  
**So that** progress is visible

**Acceptance Criteria:**
- [ ] Check boxes for all stories
- [ ] Link to this file from README
- [ ] Update checkboxes as stories are completed
- [ ] Add notes section for deviations or changes

---

#### Story 7.3: Create API Gateway Configuration Documentation
**As a** DevOps engineer  
**I want** detailed API Gateway setup instructions  
**So that** APIs can be configured correctly in the console

**Acceptance Criteria:**
- [ ] File: `reference-materials/api-gateway.md` (created in this story)
- [ ] HTTP API setup with screenshots/detailed steps
- [ ] WebSocket API setup with screenshots/detailed steps
- [ ] Integration with Lambda functions
- [ ] Testing procedures for each API
- [ ] Troubleshooting common issues

**Documentation:**
See [api-gateway.md](./api-gateway.md)

---

## Development Phases

### Phase 1: Infrastructure (Stories 1.1 - 1.5)
Foundation setup - S3 buckets, DynamoDB, IAM roles, deployment scripts

### Phase 2: HTTP API Lambda (Stories 2.1 - 2.8)
Backend for session creation and presigned URL generation

### Phase 3: WebSocket & Event Lambda (Stories 3.1 - 3.7)
Real-time notifications and S3 event handling

### Phase 4: API Gateway (Stories 4.1 - 4.3)
Manual API Gateway configuration and testing

### Phase 5: Frontend (Stories 5.1 - 5.7)
Website development and deployment

### Phase 6: Testing (Stories 6.1 - 6.3)
End-to-end validation and monitoring setup

### Phase 7: Documentation (Stories 7.1 - 7.3)
Final documentation and deployment guides

---

## Quick Start Checklist

- [ ] Clone repository
- [ ] Install AWS CLI and configure credentials
- [ ] Install Python 3.12
- [ ] Deploy CloudFormation stack (Phase 1)
- [ ] Build and deploy Lambda functions (Phases 2-3)
- [ ] Configure API Gateway manually (Phase 4)
- [ ] Update website configuration with API URLs
- [ ] Deploy website to S3 (Phase 5)
- [ ] Run end-to-end tests (Phase 6)
- [ ] Monitor CloudWatch logs for any issues

---

## Architecture Diagram

```
┌─────────────┐
│   Browser   │
│  (Web App)  │
└──────┬──────┘
       │
       ├─────── HTTP API ──────┐
       │                       │
       │                  ┌────▼─────┐
       │                  │  Lambda  │
       │                  │   HTTP   │
       │                  │ Handler  │
       │                  └────┬─────┘
       │                       │
       ├─── WebSocket API ──┐  │
       │                    │  │
       │               ┌────▼──▼─────┐
       │               │  DynamoDB   │
       │               │  (Sessions) │
       │               └─────────────┘
       │
  ┌────▼─────┐
  │ WebSocket│
  │  Lambda  │◄───── S3 Event
  └──────────┘
       │
       ▼
  ┌─────────────┐
  │     S3      │
  │  (Uploads)  │
  └─────────────┘
       ▲
       │
  ┌────┴─────┐
  │  Phone   │
  │(Scanner) │
  └──────────┘
```

---

## Technology Stack

- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Backend**: AWS Lambda (Python 3.12)
- **Storage**: Amazon S3
- **Database**: Amazon DynamoDB
- **APIs**: API Gateway (HTTP + WebSocket)
- **Infrastructure**: AWS CloudFormation
- **Monitoring**: Amazon CloudWatch

---

## Notes

- All Lambda functions must use Python's `logging` module (not `print()`)
- Configuration values should be retrieved from AWS Parameter Store
- Follow PEP 8 coding standards
- Use proper error handling with try-except blocks
- Keep Lambda functions focused and single-responsibility
- Document all manual configuration steps in `api-gateway.md`
