"""
Create Session Handler
Creates a new upload session in DynamoDB
"""
import logging
import uuid
import time
import os
from utils.dynamodb import save_session
from utils.response import success_response, error_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
SESSIONS_TABLE_NAME = os.environ.get('SESSIONS_TABLE_NAME')


def handle(event):
    """
    Creates new upload session
    
    Returns:
        - sessionId: Unique session identifier
        - expiresAt: Unix timestamp when session expires
    """
    try:
        logger.info("Creating new session")
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        current_time = int(time.time())
        expires_at = current_time + 1800  # 30 minutes from now
        
        # Create session record
        session_data = {
            'sessionId': session_id,
            'status': 'AWAITING_SCAN',
            'createdAt': current_time,
            'expiresAt': expires_at,
            'wsConnectionId': None,
            'uploadKey': None
        }
        
        # Save to DynamoDB
        save_session(session_data)
        
        logger.info(f"Session created: {session_id}")
        
        # Return response
        return success_response({
            'sessionId': session_id,
            'expiresAt': expires_at
        })
        
    except Exception as e:
        logger.error(f"Error creating session: {e}", exc_info=True)
        return error_response('Failed to create session', 500)
