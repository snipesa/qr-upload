# Mobile Upload Page Specification

## Purpose

Provide a phone-friendly upload page that completes the QR upload flow.
The QR code should open this page on the phone, which then performs:
- fetch presigned URL from the HTTP API
- prompt user to select an image
- upload the image using a PUT request

## QR Code Target

Format:
```
{websiteBaseUrl}/uploads/?sessionId={sessionId}
```

Notes:
- The QR code should not point directly to `GET /upload-url`.
- The mobile page is responsible for calling the API and uploading.

## Page Behavior

1. Read `sessionId` from the query string.
2. Call `GET {httpApiUrl}/upload-url?sessionId={sessionId}`.
3. Show a file input to select an image.
4. Upload the selected image with:
   - Method: `PUT`
   - URL: `uploadUrl` returned from API
   - Body: raw file contents
5. Show success state when upload finishes.
6. Show error state for network/API/upload failures.

## UI Requirements

- Minimal, mobile-first layout.
- Clear status text: "Loading", "Ready to upload", "Uploading", "Done".
- Show the file name after selection.
- Provide a retry button after failures.

## HTTP API Response Shape

Expected JSON:
```
{
  "uploadUrl": "https://bucket.s3.amazonaws.com/...",
  "uploadKey": "session-uploads/{sessionId}/image-..."
}
```

## Upload Notes

- Use `fetch(uploadUrl, { method: "PUT", body: file })`.
- Do not send JSON; send the raw file bytes.
- Set `Content-Type` to the file type if available.

## Success Criteria

- Phone user can select an image and complete the upload end-to-end.
- Desktop site receives `UPLOAD_COMPLETED` via WebSocket.
