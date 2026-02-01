"""
Generate Presigned URL Handler
Validates session and generates presigned S3 upload URL
"""
import logging
import time
import os
import boto3
from utils.dynamodb import get_session, update_session
from utils.response import success_response, error_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
UPLOAD_BUCKET_NAME = os.environ.get('UPLOAD_BUCKET_NAME')

# AWS clients
s3_client = boto3.client('s3')


def handle(event):
    """
    Generates presigned S3 upload URL for valid session
    
    Query Parameters:
        - sessionId: Session identifier
        
    Returns:
        - uploadUrl: Presigned S3 URL
        - uploadKey: S3 object key
    """
    try:
        # Extract sessionId from query parameters
        query_params = event.get('queryStringParameters', {})
        if not query_params or 'sessionId' not in query_params:
            logger.warning("Missing sessionId in query parameters")
            return error_response('Missing sessionId parameter', 400)
        
        session_id = query_params['sessionId']
        logger.info(f"Generating presigned URL for session: {session_id}")
        
        # Retrieve session from DynamoDB
        session = get_session(session_id)
        if not session:
            logger.warning(f"Session not found: {session_id}")
            return error_response('Session not found', 404)
        
        # Validate session is not expired
        current_time = int(time.time())
        if current_time > session.get('expiresAt', 0):
            logger.warning(f"Session expired: {session_id}")
            return error_response('Session expired', 400)
        
        # Validate session is not already completed
        if session.get('status') == 'COMPLETED':
            logger.warning(f"Session already completed: {session_id}")
            return error_response('Session already completed', 400)
        
        # Generate S3 upload key
        timestamp = int(time.time())
        upload_key = f"session-uploads/{session_id}/image-{timestamp}.jpg"
        
        # Generate presigned URL (5 minute expiration)
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': UPLOAD_BUCKET_NAME,
                'Key': upload_key,
                'ContentType': 'image/jpeg'
            },
            ExpiresIn=300  # 5 minutes
        )
        
        # Update session status and upload key
        update_session(session_id, {
            'status': 'UPLOAD_REQUESTED',
            'uploadKey': upload_key
        })
        
        logger.info(f"Presigned URL generated for session: {session_id}")
        
        return success_response({
            'uploadUrl': presigned_url,
            'uploadKey': upload_key
        })
        
    except Exception as e:
        logger.error(f"Error generating presigned URL: {e}", exc_info=True)
        return error_response('Failed to generate upload URL', 500)
