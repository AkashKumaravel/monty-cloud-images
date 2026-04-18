import boto3
from botocore.exceptions import ClientError
from .config import LOCALSTACK_ENDPOINT, S3_BUCKET

s3 = boto3.client(
    "s3",
    endpoint_url=LOCALSTACK_ENDPOINT
)


def delete_s3_object(s3_key: str):
    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=s3_key)
    except ClientError as e:
        error_code = e.response["Error"]["Code"]

        # Idempotency: treat missing object as success
        if error_code in ["NoSuchKey", "404"]:
            print(f"S3 object not found (idempotent): {s3_key}")
            return

        print(f"S3 delete error: {str(e)}")
        raise e