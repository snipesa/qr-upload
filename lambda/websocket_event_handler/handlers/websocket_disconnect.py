import logging

from utils.dynamodb import get_session_by_connection_id, update_session
from utils.response import success_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handle(event):
    """
    Handle WebSocket $disconnect by clearing the session connectionId.
    Always return 200 so API Gateway closes cleanly.
    """
    # ConnectionId uniquely identifies the WebSocket client.
    connection_id = event["requestContext"]["connectionId"]

    try:
        # Find the owning session (scan-based lookup).
        session = get_session_by_connection_id(connection_id)
        if session:
            update_session(session["sessionId"], {"wsConnectionId": None})
            logger.info("Disconnected session %s", session["sessionId"])
        else:
            logger.info("No session found for connection %s", connection_id)
    except Exception as exc:
        logger.error("Error during disconnect cleanup: %s", exc, exc_info=True)

    return success_response({"message": "Disconnected"})
