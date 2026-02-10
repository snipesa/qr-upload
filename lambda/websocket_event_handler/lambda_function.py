"""
WebSocket & S3 Event Lambda handler.
Routes WebSocket lifecycle events and S3 upload completion events.
"""
import logging
from handlers import websocket_connect, websocket_disconnect, s3_upload_completion
from utils.response import error_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Route WebSocket and S3 events to the appropriate handler.
    """
    try:
        logger.info("Received event: %s", event)

        # WebSocket lifecycle events are routed by API Gateway routeKey.
        if "requestContext" in event and "routeKey" in event["requestContext"]:
            route_key = event["requestContext"]["routeKey"]
            logger.info("WebSocket route: %s", route_key)

            if route_key == "$connect":
                return websocket_connect.handle(event)
            if route_key == "$disconnect":
                return websocket_disconnect.handle(event)

            return error_response("Unsupported route", 400)

        # S3 ObjectCreated events are delivered under Records with s3 metadata.
        if "Records" in event and event["Records"] and "s3" in event["Records"][0]:
            logger.info("S3 event received")
            return s3_upload_completion.handle(event)

        logger.warning("Unknown event type")
        return error_response("Unknown event type", 400)
    except Exception as exc:
        logger.error("Unexpected error: %s", exc, exc_info=True)
        return error_response("Internal Server Error", 500)
