# QR-Based Image Upload Web App

## 1. Project Overview

This project is a simple web application that allows a user to upload an image **from their phone** by scanning a **QR code displayed on a web app**. The upload happens directly to Amazon S3 using a **presigned URL**, and the original web app is notified in **real time** when the upload is complete using **WebSockets**.

The design is fully serverless, scalable, and cost-efficient.

---

## 2. Core User Experience Flow

### Actors

* **Web App (Browser / Kiosk / Desktop)**
* **Phone (Mobile browser after scanning QR)**
* **Backend (AWS services)**

### High-Level Flow

1. Web app loads and shows a short random informational message.
2. User clicks **Upload**.
3. Backend creates a new **upload session**.
4. Web app displays a **QR code unique to that session**.
5. User scans the QR code with their phone.
6. Phone requests permission to upload.
7. Backend generates a **presigned S3 upload URL**.
8. Phone uploads the image **directly to S3**.
9. S3 emits an upload completion event.
10. Backend notifies the web app via **WebSocket**.
11. Web app updates UI to show success.

---

## 3. AWS Services and Their Roles

### 3.1 Amazon S3

#### A. Static Website Hosting

* Hosts `index.html`, JavaScript, and CSS
* Serves the main web app UI

#### B. Image Upload Bucket

* Stores user-uploaded images
* Images uploaded directly using presigned URLs
* Organized by session-based prefixes

Example layout:

```
user-uploads-bucket/
  session-uploads/
    <sessionId>/
      image.jpg
```

---

### 3.2 Amazon API Gateway (HTTP API)

Used for **short-lived, request-response operations**.

HTTP API Endpoints:

* `POST /sessions`

  * Creates a new upload session
* `GET /upload-url?sessionId=...`

  * Validates session
  * Returns a presigned S3 upload URL

HTTP API is used when:

* The client initiates an action
* An immediate response is expected

---

### 3.3 Amazon API Gateway (WebSocket API)

Used for **real-time server-to-client notifications**.

Responsibilities:

* Maintain a persistent connection with the web app
* Allow backend services to push messages when the upload completes

WebSocket Routes:

* `$connect` – registers a browser connection
* `$disconnect` – cleans up connection state
* Optional custom routes for future extensions

---

### 3.4 AWS Lambda

Lambda functions provide all backend logic. To reduce operational overhead, the project intentionally limits the number of Lambda functions by **grouping related responsibilities into a small number of handler-based Lambdas**. Routing is handled internally based on the incoming event payload (REST, WebSocket, or S3 event).

The architecture uses **two to three Lambda functions maximum**, each with clearly separated handler files.

---

#### Lambda Group 1: HTTP API Lambda

This Lambda is integrated with **API Gateway (HTTP API)** and contains multiple handlers internally.

Handlers:

1. **Create Session Handler**

   * Triggered by `POST /sessions`
   * Generates a unique `sessionId`
   * Stores session record in DynamoDB with initial status

2. **Generate Presigned URL Handler**

   * Triggered by `GET /upload-url?sessionId=...`
   * Validates session existence and expiry
   * Generates short-lived presigned S3 PUT URL

Routing inside the Lambda is based on:

* HTTP method
* Resource path

This keeps HTTP API logic centralized while maintaining separation of concerns at the code level.

---

#### Lambda Group 2: WebSocket + Event Lambda

This Lambda handles **WebSocket lifecycle events** and **S3 upload completion events**.

Handlers:

1. **WebSocket Connect Handler**

   * Triggered by WebSocket `$connect`
   * Extracts `sessionId` from query parameters
   * Saves `connectionId` ↔ `sessionId` mapping in DynamoDB

2. **WebSocket Disconnect Handler**

   * Triggered by WebSocket `$disconnect` (when web app closes connection after success)
   * Removes or marks stale WebSocket connection data
   * Cleans up `connectionId` ↔ `sessionId` mapping in DynamoDB

3. **S3 Upload Completion Handler**

   * Triggered by S3 `ObjectCreated` events
   * Extracts `sessionId` from S3 object key or metadata
   * Updates session status to `COMPLETED`
   * Pushes notification via API Gateway WebSocket Management API
   * After success message is displayed on the web app, the WebSocket connection is terminated

Routing inside this Lambda is based on:

* Presence of `requestContext.routeKey` (WebSocket)
* Presence of `Records[].s3` (S3 event)

---

This grouping strategy:

* Reduces Lambda count
* Simplifies IAM policy management
* Keeps deployment and monitoring manageable

Each handler should still live in its own file/module to preserve clarity and testability.

---

### 3.5 Amazon DynamoDB

Used as the **session state store**.

Example item structure:

```json
{
  "sessionId": "abc123",
  "status": "AWAITING_SCAN | UPLOAD_REQUESTED | COMPLETED",
  "createdAt": 1690000000,
  "wsConnectionId": "XYZ987",
  "uploadKey": "session-uploads/abc123/image.jpg"
}
```

Features used:

* Primary key: `sessionId`
* TTL attribute to auto-expire old sessions

---

## 4. Detailed Step-by-Step System Flow

### Step 1: Web App Loads

* Static files served from S3
* Web app displays a random informational message

---

### Step 2: User Clicks Upload (HTTP API)

**Browser → HTTP API**

```
POST /sessions
```

**Backend actions**:

* Create new sessionId
* Save session to DynamoDB with status `AWAITING_SCAN`
* Return sessionId and upload URL for QR code

**Frontend actions**:

* Generate QR code using JavaScript
* Display QR code
* Open WebSocket connection using sessionId

---

### Step 3: Phone Scans QR Code (HTTP API)

QR code resolves to:

```
GET /upload-url?sessionId=<sessionId>
```

**Backend actions**:

* Validate session exists and is not expired
* Update session status to `UPLOAD_REQUESTED`
* Generate presigned S3 PUT URL
* Return presigned URL to phone

---

### Step 4: Image Upload (Direct to S3)

**Phone → S3**

* Uploads image using presigned URL
* Backend is not involved in the data transfer

---

### Step 5: Upload Completion Event (Event-driven)

**S3 → Lambda**

* S3 emits `ObjectCreated` event
* Lambda extracts sessionId from object key

**Lambda actions**:

* Update DynamoDB session status to `COMPLETED`
* Retrieve WebSocket connectionId
* Push notification via WebSocket Management API

---

### Step 6: Web App Receives Notification (WebSocket)

**Browser UI**:

* Receives `UPLOAD_COMPLETED` message
* Updates UI to show success with image/connection name
* After displaying success, closes the WebSocket connection

**WebSocket Disconnection Flow**:

* Browser closes WebSocket connection (or connection times out or browser refresh)
* API Gateway triggers `$disconnect` route
* Lambda WebSocket Disconnect Handler runs
* Connection mapping removed from DynamoDB


---

## 5. HTTP API vs WebSocket Usage Summary

| Use Case                     | Technology |
| ---------------------------- | ---------- |
| Client initiates action      | HTTP API   |
| Generate session             | HTTP API   |
| Generate presigned URL       | HTTP API   |
| Upload image                 | Direct S3  |
| Notify browser of completion | WebSocket  |
| Real-time updates            | WebSocket  |

---

## 6. Security & Best Practices

* S3 buckets block public access
* Presigned URLs:

  * Short expiration (e.g., 5 minutes)
  * Limited to specific object keys
* DynamoDB TTL cleans up old sessions
* IAM policies scoped per Lambda
* Validate sessionId on every HTTP API call

---

## 7. Recommended Implementation Order

1. Static site hosting in S3
2. DynamoDB session table
3. HTTP API – create session
4. QR code generation in frontend
5. HTTP API – presigned upload URL
6. S3 direct upload validation
7. WebSocket API setup
8. S3 event → Lambda → WebSocket notification
9. UI success handling and edge cases

---

## 8. Future Enhancements

* CloudFront in front of S3
* Image type and size validation
* Multi-image uploads per session
* Image lifecycle expiration rules
* Image moderation or processing pipeline

---

## 9. One-Sentence Mental Model

**HTTP API starts the process, S3 does the heavy lifting, and WebSockets finish the story.**
