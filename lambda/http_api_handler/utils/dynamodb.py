"""
DynamoDB Utilities
Helper functions for DynamoDB operations
"""
import logging
import os
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
SESSIONS_TABLE_NAME = os.environ.get('SESSIONS_TABLE_NAME')

# AWS clients
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(SESSIONS_TABLE_NAME)


def save_session(session_data):
    """
    Save new session to DynamoDB
    
    Args:
        session_data: Dictionary containing session attributes
    """
    try:
        logger.info(f"Saving session: {session_data.get('sessionId')}")
        table.put_item(Item=session_data)
        logger.info("Session saved successfully")
    except Exception as e:
        logger.error(f"Error saving session: {e}", exc_info=True)
        raise


def get_session(session_id):
    """
    Retrieve session by ID
    
    Args:
        session_id: Session identifier
        
    Returns:
        Session data dictionary or None if not found
    """
    try:
        logger.info(f"Retrieving session: {session_id}")
        response = table.get_item(Key={'sessionId': session_id})
        session = response.get('Item')
        
        if session:
            logger.info(f"Session found: {session_id}")
        else:
            logger.warning(f"Session not found: {session_id}")
            
        return session
    except Exception as e:
        logger.error(f"Error retrieving session: {e}", exc_info=True)
        raise


def update_session(session_id, updates):
    """
    Update session attributes
    
    Args:
        session_id: Session identifier
        updates: Dictionary of attributes to update
    """
    try:
        logger.info(f"Updating session: {session_id} with {updates}")
        
        # Build update expression dynamically
        update_expressions = []
        expression_attribute_names = {}
        expression_attribute_values = {}
        
        for key, value in updates.items():
            placeholder_name = f"#{key}"
            placeholder_value = f":{key}"
            update_expressions.append(f"{placeholder_name} = {placeholder_value}")
            expression_attribute_names[placeholder_name] = key
            expression_attribute_values[placeholder_value] = value
        
        update_expression = "SET " + ", ".join(update_expressions)
        
        table.update_item(
            Key={'sessionId': session_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )
        
        logger.info(f"Session updated successfully: {session_id}")
    except Exception as e:
        logger.error(f"Error updating session: {e}", exc_info=True)
        raise
