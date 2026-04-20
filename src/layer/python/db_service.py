import time
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from layer.python.config import LOCALSTACK_ENDPOINT, DYNAMODB_TABLE
from layer.python.utils import log
from models.image_metadata import ImageMetadata, STATUS_PENDING

dynamodb = boto3.resource("dynamodb", endpoint_url=LOCALSTACK_ENDPOINT)
table = dynamodb.Table(DYNAMODB_TABLE)


def get_image_metadata(image_id):
    response = table.get_item(Key={"image_id": image_id})
    item = response.get("Item")
    return ImageMetadata.from_item(item) if item else None


def create_image_metadata(metadata: ImageMetadata):
    table.put_item(Item=metadata.to_item())


def update_image_status(image_id, status):
    table.update_item(
        Key={"image_id": image_id},
        UpdateExpression="SET #s = :status",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":status": status}
    )


def delete_image_metadata(image_id):
    try:
        table.delete_item(Key={"image_id": image_id})
    except ClientError as e:
        log("ERROR", "DynamoDB delete failed", image_id=image_id, error=str(e))
        raise


def query_by_user(user_id, uploaded_after=None, uploaded_before=None, limit=10, exclusive_start_key=None):
    key_condition = Key("user_id").eq(user_id)

    if uploaded_after and uploaded_before:
        key_condition &= Key("uploaded_at").between(int(uploaded_after), int(uploaded_before))
    elif uploaded_after:
        key_condition &= Key("uploaded_at").gte(int(uploaded_after))
    elif uploaded_before:
        key_condition &= Key("uploaded_at").lte(int(uploaded_before))

    query_kwargs = {
        "IndexName": "user-index",
        "KeyConditionExpression": key_condition,
        "Limit": limit,
        "ScanIndexForward": False,
    }
    if exclusive_start_key:
        query_kwargs["ExclusiveStartKey"] = exclusive_start_key

    response = table.query(**query_kwargs)
    return response.get("Items", []), response.get("LastEvaluatedKey")


def query_by_file_name(file_name, limit=10, exclusive_start_key=None):
    query_kwargs = {
        "IndexName": "file-name-index",
        "KeyConditionExpression": Key("file_name").eq(file_name),
        "Limit": limit,
        "ScanIndexForward": False,
    }
    if exclusive_start_key:
        query_kwargs["ExclusiveStartKey"] = exclusive_start_key

    response = table.query(**query_kwargs)
    return response.get("Items", []), response.get("LastEvaluatedKey")


def scan_images(tag=None, limit=10, exclusive_start_key=None):
    scan_kwargs = {"Limit": limit}

    if exclusive_start_key:
        scan_kwargs["ExclusiveStartKey"] = exclusive_start_key
    if tag:
        scan_kwargs["FilterExpression"] = Attr("tags").contains(tag)

    response = table.scan(**scan_kwargs)
    return response.get("Items", []), response.get("LastEvaluatedKey")


def delete_stale_pending(max_age_seconds=86400):
    cutoff = int(time.time()) - max_age_seconds
    response = table.scan(
        FilterExpression=Attr("status").eq(STATUS_PENDING) & Attr("uploaded_at").lte(cutoff)
    )
    items = response.get("Items", [])
    for item in items:
        table.delete_item(Key={"image_id": item["image_id"]})
    return len(items)


def image_exists(image_id):
    response = table.get_item(
        Key={"image_id": image_id},
        ProjectionExpression="image_id"
    )
    return "Item" in response


def put_image_metadata(metadata: ImageMetadata):
    try:
        table.put_item(
            Item=metadata.to_item(),
            ConditionExpression="attribute_not_exists(image_id)"
        )
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            log("INFO", "Duplicate image ignored (idempotent)", image_id=metadata.image_id)
            return False
        log("ERROR", "DynamoDB put failed", error=str(e))
        raise
