import boto3
from botocore.exceptions import ClientError
from .config import LOCALSTACK_ENDPOINT, S3_BUCKET

s3_client = boto3.client("s3", endpoint_url=LOCALSTACK_ENDPOINT)


def delete_s3_object(s3_key: str):
    try:
        s3_client.delete_object(Bucket=S3_BUCKET, Key=s3_key)
    except ClientError as e:
        error_code = e.response["Error"]["Code"]

        # Idempotency: treat missing object as success
        if error_code in ["NoSuchKey", "404"]:
            print(f"S3 object not found (idempotent): {s3_key}")
            return

        print(f"S3 delete error: {str(e)}")
        raise e

def generate_presigned_download_url(s3_key: str, expires_in: int = 3600) -> str:
    return s3_client.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": S3_BUCKET,
            "Key": s3_key
        },
        ExpiresIn=expires_in
    )


# 🔥 Abstraction layer (future-proof for CDN)
def generate_download_url(s3_key: str, expires_in: int = 3600) -> str:
    """
    Today: returns S3 pre-signed URL
    Future: can switch to CloudFront signed URL
    """
    return generate_presigned_download_url(s3_key, expires_in)