"""
HTTP API Lambda Handler
Routes HTTP API requests to appropriate handlers
"""
import logging
from handlers import create_session, generate_presigned_url
from utils.response import error_response

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Entry point for HTTP API Lambda
    Routes requests based on HTTP method and path
    """
    try:
        logger.info(f"Received event: {event}")
        
        # Extract HTTP method and path
        http_method = event['requestContext']['http']['method']
        path = event['requestContext']['http']['path']
        
        logger.info(f"HTTP {http_method} {path}")
        
        # Route to appropriate handler
        if http_method == 'POST' and path == '/dev/sessions':
            return create_session.handle(event)
        elif http_method == 'GET' and path == '/dev/upload-url':
            return generate_presigned_url.handle(event)
        else:
            logger.warning(f"Route not found: {http_method} {path}")
            return error_response('Not Found', 404)
            
    except KeyError as e:
        logger.error(f"Missing required field in event: {e}")
        return error_response('Bad Request', 400)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return error_response('Internal Server Error', 500)
