import logging
import os

import boto3
from boto3.dynamodb.conditions import Attr

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_table_name = os.environ["SESSIONS_TABLE_NAME"]
_table = boto3.resource("dynamodb").Table(_table_name)


def get_session(session_id):
    response = _table.get_item(Key={"sessionId": session_id})
    return response.get("Item")


def update_session(session_id, updates):
    # Skip no-op updates to avoid DynamoDB errors.
    if not updates:
        return

    update_expressions = []
    expression_attribute_names = {}
    expression_attribute_values = {}

    for idx, (key, value) in enumerate(updates.items()):
        name_key = f"#k{idx}"
        value_key = f":v{idx}"
        update_expressions.append(f"{name_key} = {value_key}")
        expression_attribute_names[name_key] = key
        expression_attribute_values[value_key] = value

    _table.update_item(
        Key={"sessionId": session_id},
        UpdateExpression="SET " + ", ".join(update_expressions),
        ExpressionAttributeNames=expression_attribute_names,
        ExpressionAttributeValues=expression_attribute_values,
    )


def get_session_by_connection_id(connection_id):
    # Scan used as a fallback when no GSI exists for connectionId.
    response = _table.scan(
        FilterExpression=Attr("wsConnectionId").eq(connection_id),
    )
    items = response.get("Items", [])
    return items[0] if items else None
