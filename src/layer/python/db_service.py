import boto3
from boto3.dynamodb.conditions import Key, Attr
from .config import LOCALSTACK_ENDPOINT, DYNAMODB_TABLE

dynamodb = boto3.resource("dynamodb", endpoint_url=LOCALSTACK_ENDPOINT)
table = dynamodb.Table(DYNAMODB_TABLE)


def get_image_metadata(image_id: str):
    response = table.get_item(Key={"image_id": image_id})
    return response.get("Item")


def delete_image_metadata(image_id: str):
    try:
        table.delete_item(Key={"image_id": image_id})
    except Exception as e:
        print(f"DynamoDB delete error: {str(e)}")
        raise e


# 🔹 Query by user (GSI1)
def query_by_user(user_id, uploaded_after=None, uploaded_before=None, limit=10, exclusive_start_key=None):
    key_condition = Key("user_id").eq(user_id)

    if uploaded_after and uploaded_before:
        key_condition &= Key("uploaded_at").between(int(uploaded_after), int(uploaded_before))
    elif uploaded_after:
        key_condition &= Key("uploaded_at").gte(int(uploaded_after))
    elif uploaded_before:
        key_condition &= Key("uploaded_at").lte(int(uploaded_before))

    response = table.query(
        IndexName="user-index",
        KeyConditionExpression=key_condition,
        Limit=limit,
        ScanIndexForward=False,
        ExclusiveStartKey=exclusive_start_key
    )

    return response.get("Items", []), response.get("LastEvaluatedKey")


# 🔹 Query by file name (GSI2)
def query_by_file_name(file_name, limit=10, exclusive_start_key=None):
    response = table.query(
        IndexName="file-name-index",
        KeyConditionExpression=Key("file_name").eq(file_name),
        Limit=limit,
        ScanIndexForward=False,
        ExclusiveStartKey=exclusive_start_key
    )

    return response.get("Items", []), response.get("LastEvaluatedKey")


# 🔹 Scan (tag or full)
def scan_images(tag=None, limit=10, exclusive_start_key=None):
    scan_kwargs = {
        "Limit": limit
    }

    if exclusive_start_key:
        scan_kwargs["ExclusiveStartKey"] = exclusive_start_key

    if tag:
        scan_kwargs["FilterExpression"] = Attr("tags").contains(tag)

    response = table.scan(**scan_kwargs)

    return response.get("Items", []), response.get("LastEvaluatedKey")