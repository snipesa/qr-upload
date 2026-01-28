# Website Specification

## Overview
Static website for QR-based image upload application, hosted on S3.

## File Structure
```
website/
├── index.html
├── css/
│   └── styles.css
├── js/
│   ├── app.js
│   ├── qr-generator.js
│   └── websocket-client.js
└── assets/
    └── (images, icons, etc.)
```

## Components

### 1. index.html
**Purpose**: Main HTML structure

**Key Elements**:
- Container for app views
- Multiple view states: initial, QR code, success, error, loading
- Buttons: Start Upload, Cancel, Retry, New Upload
- QR code container
- Message display areas
- External library: QRCode.js (via CDN)

**View States**:
- **Initial View**: Upload button and random info message
- **QR View**: Displays QR code and instructions
- **Success View**: Shows upload completion message
- **Error View**: Displays error message with retry option
- **Loading**: Spinner for transitions

### 2. css/styles.css
**Purpose**: Styling and responsive design

**Features**:
- Gradient background
- Card-based layout
- Responsive design (mobile-first)
- Button styles with hover effects
- View transition animations
- Loading spinner
- Success/error icons

**Color Scheme**:
- Primary: Purple gradient (#667eea to #764ba2)
- Success: Green (#4caf50)
- Error: Red (#f44336)
- Background: White cards on gradient

### 3. js/app.js
**Purpose**: Main application logic

**Class**: `QRUploadApp`

**Configuration**:
```javascript
{
    httpApiUrl: 'https://{api-id}.execute-api.{region}.amazonaws.com',
    wsApiUrl: 'wss://{api-id}.execute-api.{region}.amazonaws.com/production'
}
```

**Methods**:
- `init()` - Initialize app and attach event listeners
- `displayRandomMessage()` - Show random informational message
- `startUpload()` - Create session and display QR code
- `createSession()` - Call HTTP API to create session
- `generateQRCode(url)` - Generate QR code for upload URL
- `connectWebSocket(sessionId)` - Open WebSocket connection
- `handleWebSocketMessage(data)` - Process WebSocket notifications
- `showView(viewName)` - Switch between view states
- `showSuccess(data)` - Display success message
- `showError(message)` - Display error message
- `cancelUpload()` - Cancel current upload session
- `reset()` - Reset to initial state

**State Management**:
```javascript
{
    sessionId: null,
    wsConnection: null,
    currentView: 'initial'
}
```

**Info Messages** (examples):
- "Did you know? QR codes can hold up to 4,296 alphanumeric characters!"
- "Fun fact: QR stands for 'Quick Response'"
- "Tip: Make sure your camera has good lighting when scanning"
- "QR codes were invented in Japan in 1994"
- "Upload any image format: JPEG, PNG, GIF, and more!"

### 4. js/websocket-client.js
**Purpose**: WebSocket connection wrapper

**Class**: `WebSocketClient`

**Constructor Parameters**:
- `url` - WebSocket URL with sessionId query parameter
- `callbacks` - Object with onOpen, onMessage, onError, onClose handlers

**Methods**:
- `connect()` - Establish WebSocket connection
- `send(data)` - Send message to server (JSON)
- `close()` - Close WebSocket connection

**Event Handlers**:
- `onopen` - Connection established
- `onmessage` - Receive server messages
- `onerror` - Handle connection errors
- `onclose` - Connection closed

**Message Format**:
```javascript
{
    action: 'UPLOAD_COMPLETED',
    sessionId: 'abc123',
    uploadKey: 'session-uploads/abc123/image.jpg',
    timestamp: 1234567890
}
```

### 5. js/qr-generator.js
**Purpose**: QR code generation utilities

**Library**: QRCode.js (loaded via CDN)

**Usage**:
```javascript
new QRCode(container, {
    text: url,
    width: 256,
    height: 256,
    colorDark: "#000000",
    colorLight: "#ffffff",
    correctLevel: QRCode.CorrectLevel.H
});
```

**QR Code Content**:
Format: `{httpApiUrl}/upload-url?sessionId={sessionId}`

## User Flow

1. **Page Load**
   - Display random informational message
   - Show "Start Upload" button

2. **Start Upload**
   - Show loading spinner
   - Call HTTP API: `POST /sessions`
   - Receive sessionId
   - Generate QR code with upload URL
   - Open WebSocket connection with sessionId
   - Display QR code view

3. **Waiting for Upload**
   - QR code displayed
   - WebSocket connection active
   - User can cancel

4. **Upload Complete**
   - Receive WebSocket message
   - Display success view
   - Close WebSocket connection
   - Show "Start New Upload" button

5. **Error Handling**
   - Display error message
   - Show "Try Again" button
   - Close WebSocket if open

## API Integration

### HTTP API Calls

**Create Session**:
```javascript
POST {httpApiUrl}/sessions
Response: {
    sessionId: "uuid",
    expiresAt: timestamp
}
```

**QR Code URL**:
```
{httpApiUrl}/upload-url?sessionId={sessionId}
```
(This URL is embedded in QR code for phone to scan)

### WebSocket Connection

**Connection URL**:
```
{wsApiUrl}?sessionId={sessionId}
```

**Received Messages**:
```javascript
{
    action: "UPLOAD_COMPLETED",
    sessionId: "uuid",
    uploadKey: "s3/key/path",
    timestamp: 1234567890
}
```

## Error Handling

**Scenarios**:
- Failed to create session (HTTP API error)
- WebSocket connection failed
- Session expired
- Upload failed
- Network errors

**User Feedback**:
- Display clear error message
- Provide retry option
- Log errors to console for debugging

## Testing Checklist

- [ ] Page loads without errors
- [ ] Random message displays on load
- [ ] Start Upload creates session successfully
- [ ] QR code generates correctly
- [ ] QR code is scannable
- [ ] WebSocket connects successfully
- [ ] Upload completion triggers success view
- [ ] WebSocket disconnects after success
- [ ] Cancel button works
- [ ] New Upload resets app state
- [ ] Error handling works for all scenarios
- [ ] Responsive design on mobile devices
- [ ] Responsive design on tablets
- [ ] Responsive design on desktop
- [ ] Works in Chrome, Firefox, Safari
- [ ] Console shows no errors

## Configuration

Before deployment, update `js/app.js`:

```javascript
this.config = {
    httpApiUrl: 'https://YOUR_HTTP_API_ID.execute-api.REGION.amazonaws.com',
    wsApiUrl: 'wss://YOUR_WS_API_ID.execute-api.REGION.amazonaws.com/production'
};
```

Replace:
- `YOUR_HTTP_API_ID` - From API Gateway HTTP API
- `YOUR_WS_API_ID` - From API Gateway WebSocket API
- `REGION` - Your AWS region (e.g., us-east-1)

## Deployment

**S3 Bucket Configuration**:
- Static website hosting enabled
- Index document: `index.html`
- Error document: `index.html`
- Public read access
- CORS enabled for API calls

**Cache Headers**:
- HTML: `no-cache, no-store, must-revalidate`
- CSS/JS: `max-age=86400` (1 day)
- Assets: `max-age=31536000` (1 year)

## Performance Optimization

- Minify CSS and JavaScript for production
- Use CDN for external libraries
- Lazy load images if any
- Enable gzip compression
- Consider CloudFront for production

## Security Considerations

- HTTPS only in production
- CORS properly configured
- No sensitive data in client-side code
- Validate all user inputs
- Handle WebSocket disconnections gracefully
