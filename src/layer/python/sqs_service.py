import json
import boto3
from layer.python.config import LOCALSTACK_ENDPOINT, DELETE_QUEUE_URL
from layer.python.utils import log

sqs = boto3.client("sqs", endpoint_url=LOCALSTACK_ENDPOINT)


def send_delete_message(message):
    try:
        sqs.send_message(
            QueueUrl=DELETE_QUEUE_URL,
            MessageBody=json.dumps(message)
        )
    except Exception as e:
        log("ERROR", "SQS send failed", error=str(e))
        raise
