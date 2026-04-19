import os
import json
import pytest
import boto3
from moto import mock_aws

os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SECURITY_TOKEN"] = "testing"
os.environ["AWS_SESSION_TOKEN"] = "testing"
os.environ["LOCALSTACK_ENDPOINT"] = ""
os.environ["S3_PRESIGN_ENDPOINT"] = ""
os.environ["DYNAMODB_TABLE"] = "image-metadata"
os.environ["S3_BUCKET"] = "image-service-bucket"
os.environ["DELETE_QUEUE_URL"] = "https://sqs.us-east-1.amazonaws.com/000000000000/delete-queue"

BUCKET = os.environ["S3_BUCKET"]
TABLE = os.environ["DYNAMODB_TABLE"]


@pytest.fixture
def aws():
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=BUCKET)

        sqs = boto3.client("sqs", region_name="us-east-1")
        queue = sqs.create_queue(QueueName="delete-queue")
        os.environ["DELETE_QUEUE_URL"] = queue["QueueUrl"]

        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName=TABLE,
            AttributeDefinitions=[
                {"AttributeName": "image_id", "AttributeType": "S"},
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "uploaded_at", "AttributeType": "N"},
                {"AttributeName": "file_name", "AttributeType": "S"},
            ],
            KeySchema=[{"AttributeName": "image_id", "KeyType": "HASH"}],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "user-index",
                    "KeySchema": [
                        {"AttributeName": "user_id", "KeyType": "HASH"},
                        {"AttributeName": "uploaded_at", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
                },
                {
                    "IndexName": "file-name-index",
                    "KeySchema": [
                        {"AttributeName": "file_name", "KeyType": "HASH"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
                },
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )

        import layer.python.db_service as db_mod
        import layer.python.s3_service as s3_mod
        import layer.python.sqs_service as sqs_mod

        db_mod.dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        db_mod.table = db_mod.dynamodb.Table(TABLE)
        s3_mod.s3_client = boto3.client("s3", region_name="us-east-1")
        s3_mod.s3_presign_client = boto3.client("s3", region_name="us-east-1")
        sqs_mod.sqs = boto3.client("sqs", region_name="us-east-1")

        yield {"s3": s3, "ddb": ddb, "table": ddb.Table(TABLE), "sqs": sqs}


def apigw_event(body=None, path_params=None, query_params=None, headers=None):
    return {
        "body": json.dumps(body) if body else None,
        "pathParameters": path_params,
        "queryStringParameters": query_params,
        "headers": headers or {},
    }


def seed_image(table, image_id="img-1", user_id="user-1", s3_key="img-1_photo.jpg",
               file_name="photo.jpg", uploaded_at=1704067200, status="COMPLETED"):
    item = {
        "image_id": image_id,
        "user_id": user_id,
        "s3_key": s3_key,
        "file_name": file_name,
        "uploaded_at": uploaded_at,
        "tags": [],
        "status": status,
    }
    table.put_item(Item=item)
    return item


class MockLambdaContext:
    def __init__(self, remaining_millis=30000):
        self._remaining = remaining_millis

    def get_remaining_time_in_millis(self):
        return self._remaining
