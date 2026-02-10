import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def send_message(connection_id, data):
    # API Gateway Management API requires the WebSocket API endpoint.
    endpoint = os.environ.get("WS_API_ENDPOINT")
    if not endpoint:
        logger.error("WS_API_ENDPOINT is not set")
        return False

    # Use the Management API to post data to a specific connection.
    api_client = boto3.client(
        "apigatewaymanagementapi",
        endpoint_url=f"https://{endpoint}",
    )

    try:
        api_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(data).encode("utf-8"),
        )
        return True
    except api_client.exceptions.GoneException:
        logger.info("Stale WebSocket connection: %s", connection_id)
        return False
    except Exception as exc:
        logger.error("Error sending WebSocket message: %s", exc, exc_info=True)
        raise
