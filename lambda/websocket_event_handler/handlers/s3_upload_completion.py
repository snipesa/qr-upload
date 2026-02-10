import logging
import os
import time
import urllib.parse

from utils.dynamodb import get_session, update_session
from utils.response import error_response, success_response
from utils.websocket import send_message

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _extract_session_id(s3_key):
    # Expected key format: session-uploads/{sessionId}/image-...
    parts = s3_key.split("/")
    if len(parts) < 2 or parts[0] != "session-uploads":
        return None
    return parts[1]


def handle(event):
    """
    Handle S3 ObjectCreated events and notify the WebSocket client.
    """
    # Process the first S3 record (single-object uploads).
    record = event["Records"][0]
    s3_key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
    session_id = _extract_session_id(s3_key)

    if not session_id:
        logger.warning("Unable to parse sessionId from key: %s", s3_key)
        return error_response("Invalid S3 key", 400)

    # Load the session to update status and notify the client.
    session = get_session(session_id)
    if not session:
        logger.warning("Session not found for upload key: %s", s3_key)
        return error_response("Session not found", 404)

    update_session(
        session_id,
        {
            "status": "COMPLETED",
            "uploadKey": s3_key,
            "completedAt": int(time.time()),
        },
    )

    # Notify the connected WebSocket client if available.
    connection_id = session.get("wsConnectionId")
    ws_endpoint = os.environ.get("WS_API_ENDPOINT")
    if connection_id and ws_endpoint:
        message = {
            "action": "UPLOAD_COMPLETED",
            "sessionId": session_id,
            "uploadKey": s3_key,
            "timestamp": int(time.time()),
        }
        sent = send_message(connection_id, message)
        if not sent:
            logger.info("Stale connection %s; clearing from session", connection_id)
            update_session(session_id, {"wsConnectionId": None})
    else:
        logger.info("No WebSocket notification sent (missing connection or endpoint)")

    return success_response({"message": "Upload processed"})
