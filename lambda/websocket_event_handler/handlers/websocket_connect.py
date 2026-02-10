import logging
import time
import uuid

from utils.dynamodb import get_session, update_session
from utils.response import error_response, success_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _is_valid_uuid(value):
    # Accept string UUIDs from API Gateway query parameters.
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False


def handle(event):
    """
    Handle WebSocket $connect by attaching connectionId to the session.
    """
    # API Gateway supplies the connectionId in requestContext.
    connection_id = event["requestContext"]["connectionId"]
    # SessionId comes from the connect URL query string.
    query_params = event.get("queryStringParameters") or {}
    session_id = query_params.get("sessionId")

    if not session_id:
        return error_response("Missing sessionId", 400)

    if not _is_valid_uuid(session_id):
        return error_response("Invalid sessionId", 404)

    # Validate the session exists and is still active.
    session = get_session(session_id)
    if not session:
        return error_response("Session not found", 404)

    expires_at = session.get("expiresAt")
    if expires_at and int(expires_at) < int(time.time()):
        return error_response("Session expired", 400)

    update_session(session_id, {"wsConnectionId": connection_id})

    logger.info("Connected session %s to %s", session_id, connection_id)
    return success_response({"message": "Connected"})
