import boto3
import json
from .config import LOCALSTACK_ENDPOINT, DELETE_QUEUE_URL

sqs = boto3.client(
    "sqs",
    endpoint_url=LOCALSTACK_ENDPOINT
)


def send_delete_message(message: dict):
    try:
        sqs.send_message(
            QueueUrl=DELETE_QUEUE_URL,
            MessageBody=json.dumps(message)
        )
    except Exception as e:
        print(f"SQS send error: {str(e)}")
        raise e