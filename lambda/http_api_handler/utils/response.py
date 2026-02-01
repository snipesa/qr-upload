"""
Response Utilities
Helper functions for creating HTTP responses
"""
import json


def success_response(data, status_code=200):
    """
    Create successful HTTP response
    
    Args:
        data: Response data to be JSON serialized
        status_code: HTTP status code (default: 200)
        
    Returns:
        API Gateway response object
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps(data)
    }


def error_response(message, status_code=500):
    """
    Create error HTTP response
    
    Args:
        message: Error message
        status_code: HTTP status code (default: 500)
        
    Returns:
        API Gateway response object
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps({'error': message})
    }
