# Lambda Functions Specification

## Overview
Two Python Lambda functions handling HTTP API requests, WebSocket lifecycle, and S3 events.

## Technology
- **Runtime**: Python 3.11+
- **Dependencies**: boto3 (AWS SDK)
- **Packaging**: ZIP file with dependencies

## File Structure
```
lambda/
├── requirements.txt
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

## Lambda 1: HTTP API Handler

### Purpose
Handle HTTP API requests for session creation and presigned URL generation.

### Configuration
- **Function Name**: `qr-upload-http-api-{environment}`
- **Runtime**: Python 3.11
- **Handler**: `lambda_function.lambda_handler`
- **Timeout**: 30 seconds
- **Memory**: 256 MB

### Environment Variables
```python
SESSIONS_TABLE_NAME = os.environ['SESSIONS_TABLE_NAME']
UPLOAD_BUCKET_NAME = os.environ['UPLOAD_BUCKET_NAME']
```

### IAM Permissions Required
- `dynamodb:GetItem` on Sessions table
- `dynamodb:PutItem` on Sessions table
- `dynamodb:UpdateItem` on Sessions table
- `s3:PutObject` on Upload bucket (for presigned URL generation)
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

### Entry Point: lambda_function.py

**Handler Signature**:
```python
def lambda_handler(event, context):
    """
    Routes HTTP API requests to appropriate handlers
    """
```

**Routing Logic**:
```python
http_method = event['requestContext']['http']['method']
path = event['requestContext']['http']['path']

if http_method == 'POST' and path == '/sessions':
    return create_session.handle(event)
elif http_method == 'GET' and path == '/upload-url':
    return generate_presigned_url.handle(event)
else:
    return error_response('Not Found', 404)
```

**Event Structure** (HTTP API v2.0):
```python
{
    'requestContext': {
        'http': {
            'method': 'POST',
            'path': '/sessions'
        },
        'requestId': '...'
    },
    'queryStringParameters': {...},
    'body': '...'  # JSON string or None
}
```

### Handler: create_session.py

**Purpose**: Create new upload session

**Function**:
```python
def handle(event):
    """
    Creates new session in DynamoDB
    Returns sessionId and expiration time
    """
```

**Logic**:
1. Generate unique sessionId using `uuid.uuid4()`
2. Calculate expiration time (30 minutes from now)
3. Create session record:
   ```python
   {
       'sessionId': str(uuid),
       'status': 'AWAITING_SCAN',
       'createdAt': int(time.time()),
       'expiresAt': int(time.time() + 1800),  # 30 minutes
       'wsConnectionId': None,
       'uploadKey': None
   }
   ```
4. Save to DynamoDB
5. Return success response with sessionId

**Response**:
```python
{
    'statusCode': 200,
    'headers': {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
    },
    'body': json.dumps({
        'sessionId': 'uuid-here',
        'expiresAt': 1234567890
    })
}
```

**Error Handling**:
- DynamoDB errors → 500 Internal Server Error
- Log all errors with traceback

### Handler: generate_presigned_url.py

**Purpose**: Generate presigned S3 URL for image upload

**Function**:
```python
def handle(event):
    """
    Validates session and generates presigned S3 URL
    """
```

**Logic**:
1. Extract `sessionId` from query parameters
2. Validate sessionId format (UUID)
3. Retrieve session from DynamoDB
4. Validate session:
   - Exists
   - Not expired
   - Not already completed
5. Generate S3 key: `session-uploads/{sessionId}/image-{timestamp}`
6. Create presigned PUT URL (5 minute expiration)
7. Update session status to `UPLOAD_REQUESTED`
8. Save uploadKey to session
9. Return presigned URL

**Presigned URL Parameters**:
```python
s3_client.generate_presigned_url(
    'put_object',
    Params={
        'Bucket': UPLOAD_BUCKET_NAME,
        'Key': upload_key,
        'ContentType': 'image/*'
    },
    ExpiresIn=300  # 5 minutes
)
```

**Response**:
```python
{
    'statusCode': 200,
    'headers': {...},
    'body': json.dumps({
        'uploadUrl': 'https://s3.amazonaws.com/...',
        'uploadKey': 'session-uploads/uuid/image-123'
    })
}
```

**Error Responses**:
- Missing sessionId → 400 Bad Request
- Invalid sessionId → 404 Not Found
- Expired session → 400 Bad Request
- Already completed → 400 Bad Request
- DynamoDB/S3 errors → 500 Internal Server Error

### Utility: utils/dynamodb.py

**Functions**:

```python
def save_session(session_data):
    """Save new session to DynamoDB"""
    table.put_item(Item=session_data)

def get_session(session_id):
    """Retrieve session by ID"""
    response = table.get_item(Key={'sessionId': session_id})
    return response.get('Item')

def update_session(session_id, updates):
    """Update session attributes"""
    # Build UpdateExpression dynamically
    # Use ExpressionAttributeNames and ExpressionAttributeValues
    table.update_item(
        Key={'sessionId': session_id},
        UpdateExpression='SET ...',
        ExpressionAttributeNames={...},
        ExpressionAttributeValues={...}
    )
```

### Utility: utils/response.py

**Functions**:

```python
def success_response(data, status_code=200):
    """Create successful HTTP response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps(data)
    }

def error_response(message, status_code=500):
    """Create error HTTP response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({'error': message})
    }
```

---

## Lambda 2: WebSocket & Event Handler

### Purpose
Handle WebSocket lifecycle events ($connect, $disconnect) and S3 upload completion events.

### Configuration
- **Function Name**: `qr-upload-websocket-event-{environment}`
- **Runtime**: Python 3.11
- **Handler**: `lambda_function.lambda_handler`
- **Timeout**: 60 seconds
- **Memory**: 256 MB

### Environment Variables
```python
SESSIONS_TABLE_NAME = os.environ['SESSIONS_TABLE_NAME']
WS_API_ENDPOINT = os.environ['WS_API_ENDPOINT']
# Format: {api-id}.execute-api.{region}.amazonaws.com/{stage}
```

### IAM Permissions Required
- `dynamodb:GetItem`, `dynamodb:UpdateItem`, `dynamodb:Scan` on Sessions table
- `execute-api:ManageConnections` for WebSocket API
- `s3:GetObject` on Upload bucket
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

### Event Triggers
1. API Gateway WebSocket: `$connect` route
2. API Gateway WebSocket: `$disconnect` route
3. S3 Event: `ObjectCreated:*` on `session-uploads/` prefix

### Entry Point: lambda_function.py

**Handler Signature**:
```python
def lambda_handler(event, context):
    """
    Routes events to appropriate handlers based on event type
    """
```

**Routing Logic**:
```python
# WebSocket events
if 'requestContext' in event and 'routeKey' in event['requestContext']:
    route_key = event['requestContext']['routeKey']
    
    if route_key == '$connect':
        return websocket_connect.handle(event)
    elif route_key == '$disconnect':
        return websocket_disconnect.handle(event)

# S3 events
elif 'Records' in event and 's3' in event['Records'][0]:
    return s3_upload_completion.handle(event)

else:
    return error_response('Unknown event type', 400)
```

### Handler: websocket_connect.py

**Purpose**: Register WebSocket connection

**Function**:
```python
def handle(event):
    """
    Save connectionId for session
    """
```

**Logic**:
1. Extract `connectionId` from event
2. Extract `sessionId` from query parameters
3. Validate sessionId
4. Retrieve session from DynamoDB
5. Validate session exists and not expired
6. Update session with `wsConnectionId`
7. Return success response

**Event Structure**:
```python
{
    'requestContext': {
        'routeKey': '$connect',
        'connectionId': 'abc123xyz'
    },
    'queryStringParameters': {
        'sessionId': 'uuid-here'
    }
}
```

**Response**:
```python
{
    'statusCode': 200,
    'body': json.dumps({'message': 'Connected'})
}
```

**Error Handling**:
- Missing sessionId → 400 with error message (connection rejected)
- Invalid session → 404 (connection rejected)
- DynamoDB errors → 500 (connection rejected)

### Handler: websocket_disconnect.py

**Purpose**: Clean up WebSocket connection

**Function**:
```python
def handle(event):
    """
    Remove connectionId from session
    """
```

**Logic**:
1. Extract `connectionId` from event
2. Find session by connectionId (scan or GSI)
3. If session found, clear `wsConnectionId`
4. Return success (always, even if session not found)

**Note**: Always return 200 to avoid connection issues

### Handler: s3_upload_completion.py

**Purpose**: Notify web app when upload completes

**Function**:
```python
def handle(event):
    """
    Process S3 upload event and send WebSocket notification
    """
```

**Logic**:
1. Parse S3 event record:
   ```python
   record = event['Records'][0]
   bucket = record['s3']['bucket']['name']
   key = urllib.parse.unquote_plus(record['s3']['object']['key'])
   ```
2. Extract sessionId from S3 key (format: `session-uploads/{sessionId}/image-xxx`)
3. Retrieve session from DynamoDB
4. Update session:
   - status: `COMPLETED`
   - uploadKey: S3 key
   - completedAt: current timestamp
5. Send WebSocket notification if connectionId exists
6. Handle stale connections gracefully

**S3 Event Structure**:
```python
{
    'Records': [{
        's3': {
            'bucket': {'name': 'bucket-name'},
            'object': {
                'key': 'session-uploads/uuid/image-123',
                'size': 12345
            }
        }
    }]
}
```

**WebSocket Message**:
```python
{
    'action': 'UPLOAD_COMPLETED',
    'sessionId': 'uuid',
    'uploadKey': 's3-key',
    'timestamp': 1234567890
}
```

### Utility: utils/websocket.py

**Functions**:

```python
def send_message(connection_id, data):
    """
    Send message to WebSocket connection
    """
    api_client = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=f'https://{WS_API_ENDPOINT}'
    )
    
    try:
        api_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(data).encode('utf-8')
        )
    except api_client.exceptions.GoneException:
        # Connection is stale
        print(f'Stale connection: {connection_id}')
        # Optionally trigger cleanup
    except Exception as e:
        print(f'Error sending message: {e}')
        raise
```

### Utility: utils/dynamodb.py

**Functions** (same as HTTP handler, plus):

```python
def get_session_by_connection_id(connection_id):
    """
    Find session by WebSocket connection ID
    Note: Consider using Global Secondary Index for production
    """
    response = table.scan(
        FilterExpression='wsConnectionId = :conn_id',
        ExpressionAttributeValues={':conn_id': connection_id}
    )
    
    items = response.get('Items', [])
    return items[0] if items else None
```

---

## Shared Utilities

### shared/constants.py

```python
SESSION_STATUS = {
    'AWAITING_SCAN': 'AWAITING_SCAN',
    'UPLOAD_REQUESTED': 'UPLOAD_REQUESTED',
    'COMPLETED': 'COMPLETED'
}

SESSION_EXPIRY_MINUTES = 30
PRESIGNED_URL_EXPIRY_SECONDS = 300

WEBSOCKET_ACTIONS = {
    'UPLOAD_COMPLETED': 'UPLOAD_COMPLETED',
    'ERROR': 'ERROR'
}
```

### shared/validators.py

```python
import uuid

def validate_session_id(session_id):
    """Validate UUID format"""
    if not session_id:
        return False, 'sessionId is required'
    
    try:
        uuid.UUID(session_id)
        return True, None
    except ValueError:
        return False, 'Invalid sessionId format'

def validate_session(session):
    """Validate session state"""
    if not session:
        return False, 'Session not found'
    
    if int(time.time()) > session.get('expiresAt', 0):
        return False, 'Session expired'
    
    return True, None
```

---

## Dependencies: requirements.txt

```txt
boto3>=1.26.0
```

**Note**: boto3 is included in Lambda runtime, but specify version for local testing

---

## Packaging for Deployment

### Create ZIP Files

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt -t package/

# Package HTTP API handler
cd package
zip -r ../http_api_handler.zip .
cd ..
cd http_api_handler
zip -r ../http_api_handler.zip . -x "*.pyc" -x "*__pycache__*"
cd ..

# Package WebSocket/Event handler
cd package
zip -r ../websocket_event_handler.zip .
cd ..
cd websocket_event_handler
zip -r ../websocket_event_handler.zip . -x "*.pyc" -x "*__pycache__*"
cd ..

# Add shared utilities to both
cd shared
zip -r ../http_api_handler.zip . -x "*.pyc" -x "*__pycache__*"
zip -r ../websocket_event_handler.zip . -x "*.pyc" -x "*__pycache__*"
```

---

## Testing

### Unit Tests

**Test Structure**:
```
lambda/
├── tests/
│   ├── __init__.py
│   ├── test_http_api_handler.py
│   ├── test_websocket_handler.py
│   ├── test_dynamodb_utils.py
│   └── test_validators.py
```

**Mock AWS Services**:
- Use `moto` library for mocking boto3 calls
- Mock DynamoDB, S3, API Gateway Management API

### Local Testing

```python
# Test HTTP API handler
event = {
    'requestContext': {
        'http': {'method': 'POST', 'path': '/sessions'}
    }
}
response = lambda_handler(event, None)
print(response)
```

### Integration Testing

- Test with actual DynamoDB local
- Test with localstack for S3
- Test WebSocket connections with wscat or Python websocket client

---

## Error Handling Best Practices

1. **Logging**:
   - Log all errors with full traceback
   - Log important events (session created, upload completed)
   - Use structured logging (JSON) for CloudWatch Insights

2. **Exceptions**:
   - Catch specific exceptions (boto3 errors)
   - Always return proper HTTP response
   - Don't expose internal errors to clients

3. **Retries**:
   - Lambda retries automatically for failures
   - Implement exponential backoff for external calls
   - Make handlers idempotent

4. **Validation**:
   - Validate all inputs before processing
   - Return clear error messages
   - Use shared validators for consistency

---

## Performance Optimization

1. **Cold Starts**:
   - Keep Lambda warm with CloudWatch Events (optional)
   - Minimize dependencies
   - Initialize boto3 clients outside handler

2. **DynamoDB**:
   - Use consistent reads only when necessary
   - Batch operations where possible
   - Consider GSI for query by connectionId

3. **Logging**:
   - Use appropriate log levels
   - Disable verbose logging in production
   - Use sampling for high-frequency events

---

## Security Considerations

1. **IAM Least Privilege**:
   - Scope permissions to specific resources
   - Use separate roles for each Lambda

2. **Input Validation**:
   - Validate all user inputs
   - Sanitize S3 keys
   - Check session expiration

3. **Secrets Management**:
   - Don't hardcode credentials
   - Use environment variables
   - Consider AWS Secrets Manager for sensitive data

4. **Error Messages**:
   - Don't expose internal details
   - Generic error messages to clients
   - Detailed logs for debugging

---

## Monitoring

### CloudWatch Metrics
- Invocation count
- Error count
- Duration
- Throttles

### CloudWatch Logs
- Log all invocations
- Log errors with context
- Use log insights for analysis

### Custom Metrics
- Session creation rate
- Upload completion rate
- WebSocket connection failures
- Average session duration

### Alarms
- Error rate > 5%
- Duration > 10 seconds
- Throttle count > 0
