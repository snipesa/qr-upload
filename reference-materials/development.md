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
- [x] Bucket name: `qr-upload-website-{environment}`
- [x] Static website hosting enabled
- [x] Index document: `index.html`
- [x] Error document: `index.html`
- [x] Public read access enabled via bucket policy
- [x] CORS configured for API calls
- [x] CloudFormation template created in `infra/cloudformation/template.yaml`
- [x] Outputs include website URL

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
- [x] Bucket name: `qr-upload-uploads-{environment}`
- [x] Public access blocked (private bucket)
- [x] CORS configured for presigned URL uploads (PUT method)
- [x] Lifecycle policy: Delete objects after 30 days
- [x] Event notification configured to trigger Lambda on object creation
- [x] CloudFormation template updated
- [x] Prefix pattern: `session-uploads/{sessionId}/`

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
- [x] Table name: `qr-upload-sessions-{environment}`
- [x] Primary key: `sessionId` (String)
- [x] Attributes: `connectionId`, `status`, `uploadUrl`, `createdAt`, `expiresAt`
- [x] TTL enabled on `expiresAt` attribute (1-hour expiration)
- [x] Billing mode: PAY_PER_REQUEST
- [x] CloudFormation template updated
- [x] Global Secondary Index (optional): `connectionId` for WebSocket lookups

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
- [x] HTTP API Lambda role with permissions:
  - `dynamodb:GetItem`, `PutItem`, `UpdateItem`, `Query` on sessions table
  - `s3:PutObject`, `PutObjectAcl` on upload bucket (for presigned URL generation)
  - CloudWatch Logs write access (via AWSLambdaBasicExecutionRole)
- [x] WebSocket/Event Lambda role with permissions:
  - `dynamodb:GetItem`, `UpdateItem`, `Scan` on sessions table
  - `execute-api:ManageConnections` for WebSocket API
  - `s3:GetObject` on upload bucket
  - CloudWatch Logs write access (via AWSLambdaBasicExecutionRole)
- [x] Roles follow naming convention: `qr-upload-{function-type}-role-{environment}`
- [x] CloudFormation template updated

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
- [x] Script: `infra/cloudformation/deploy-stack.sh`
- [x] Accepts environment parameter (dev/prod)
- [x] Creates/updates CloudFormation stack
- [x] Validates template before deployment
- [x] Displays stack outputs after deployment
- [x] Error handling for failed deployments
- [x] Usage: `./deploy-main-stack.sh dev`

**Technical Notes:**
```bash
#!/bin/bash
ENVIRONMENT=$1
STACK_NAME="qr-upload-${ENVIRONMENT}"
aws cloudformation deploy \
  --template-file template.yaml \
  --stack-name $STACK_NAME \
  --parameter-overrides Environment=$ENVIRONMENT \
  --capabilities CAPABILITY_IAM
```

---

### Epic 2: Lambda Functions - HTTP API Handler

#### Story 2: Build HTTP API Lambda
**As a** backend developer  
**I want** the HTTP API Lambda implemented and packaged  
**So that** session creation and presigned URL generation work

**Acceptance Criteria:**
- [x] Structure in `lambda/http_api_handler/` matches [lambda-specification.md](./lambda-specification.md)
- [x] `requirements.txt` scoped to HTTP API Lambda
- [x] Entry point routes POST `/sessions` and GET `/upload-url`
- [x] Handlers implemented: `create_session.py`, `generate_presigned_url.py`
- [x] Utilities implemented: `dynamodb.py`, `response.py`
- [x] Build/package output for HTTP API Lambda ZIP
- [x] Deployed via CloudFormation

---

### Epic 3: Lambda Functions - WebSocket & Event Handler

#### Story 3: Build WebSocket/Event Lambda
**As a** backend developer  
**I want** the WebSocket/Event Lambda implemented and packaged  
**So that** WebSocket lifecycle and S3 upload events are handled

**Acceptance Criteria:**
- [x] Structure in `lambda/websocket_event_handler/` matches [lambda-specification.md](./lambda-specification.md)
- [x] `requirements.txt` scoped to WebSocket/Event Lambda
- [x] Entry point routes `$connect`, `$disconnect`, and S3 `ObjectCreated` events
- [x] Handlers implemented: `websocket_connect.py`, `websocket_disconnect.py`, `s3_upload_completion.py`
- [x] Utilities implemented: `dynamodb.py`, `websocket.py`, `response.py`
- [x] Build/package output for WebSocket/Event Lambda ZIP
- [x] Deployed via CloudFormation with WebSocket and S3 triggers wired

---

### Epic 4: API Gateway Configuration

#### Story 4.1: Document HTTP API Configuration
**As a** DevOps engineer  
**I want** documentation for creating the HTTP API in API Gateway  
**So that** the API can be set up manually in the console

**Acceptance Criteria:**
- [x] Documentation file: `reference-materials/api-gateway.md`
- [x] HTTP API section with step-by-step console instructions
- [x] Endpoint definitions: POST `/sessions`, GET `/upload-url`
- [x] Lambda integration configuration for each route
- [x] CORS configuration
- [x] Stage deployment (e.g., `production`)
- [x] API URL format and example

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

### Epic 5: Website Development

#### Story 5: Build Website (Minimal UI, Dev Only)
**As a** frontend developer  
**I want** a simple web app that integrates with the APIs  
**So that** users can upload via QR and receive real-time updates

**Acceptance Criteria:**
- [ ] Basic HTML/CSS/JS in `website/` (no focus on styling)
- [ ] HTTP API integration for `POST /sessions` and `GET /upload-url`
- [ ] QR code generation for the upload link
- [ ] WebSocket client connects with `sessionId` and handles upload-complete message
- [ ] S3 static site hosting only (no CloudFront)
- [ ] Single environment: `dev`
- [ ] Simple deploy script or documented steps to sync to the S3 bucket

**Documentation:**
See [website-specification.md](./website-specification.md) for implementation details

---

### Epic 6: Documentation & Deployment

#### Story 6.1: Create Root README with Deployment Commands
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

#### Story 6.2: Update Development.md with Progress
**As a** project manager  
**I want** development.md to track completed stories  
**So that** progress is visible

**Acceptance Criteria:**
- [ ] Check boxes for all stories
- [ ] Link to this file from README
- [ ] Update checkboxes as stories are completed
- [ ] Add notes section for deviations or changes

---

## Development Phases

### Phase 1: Infrastructure (Stories 1.1 - 1.5)
Foundation setup - S3 buckets, DynamoDB, IAM roles, deployment scripts

### Phase 2: HTTP API Lambda (Story 2)
Backend for session creation and presigned URL generation

### Phase 3: WebSocket & Event Lambda (Story 3)
Real-time notifications and S3 event handling

### Phase 4: API Gateway (Stories 4.1 - 4.3)
Manual API Gateway configuration and testing

### Phase 5: Frontend (Story 5)
Website development and deployment

### Phase 6: Documentation (Stories 6.1 - 6.3)
Final documentation and deployment guides

---

## Quick Start Checklist

- [ ] Clone repository
- [ ] Install AWS CLI and configure credentials
- [ ] Install Python 3.12
- [ ] Deploy CloudFormation stack (Phase 1)
- [ ] Build and deploy Lambda functions (Phases 2-3)
- [ ] Configure API Gateway manually (Phase 4)
- [ ] Configure website with API URLs (dev)
- [ ] Deploy website to S3 (Phase 5)
- [ ] Run end-to-end tests (Phase 6)
- [ ] Monitor CloudWatch logs for any issues

---

## Architecture Diagram


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
