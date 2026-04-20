import boto3
from botocore.exceptions import ClientError
from layer.python.config import LOCALSTACK_ENDPOINT, S3_BUCKET, S3_PRESIGN_ENDPOINT
from layer.python.constants import UPLOAD_URL_EXPIRY, DOWNLOAD_URL_EXPIRY
from layer.python.utils import log

s3_client = boto3.client("s3", endpoint_url=LOCALSTACK_ENDPOINT)
s3_presign_client = boto3.client("s3", endpoint_url=S3_PRESIGN_ENDPOINT)


def generate_presigned_upload_url(image_id, file_name, expires_in=UPLOAD_URL_EXPIRY):
    s3_key = f"{image_id}_{file_name}"
    try:
        url = s3_presign_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": S3_BUCKET, "Key": s3_key},
            ExpiresIn=expires_in
        )
        return url, s3_key
    except ClientError as e:
        log("ERROR", "S3 presigned upload failed", error=str(e))
        raise


def generate_presigned_download_url(s3_key, expires_in=DOWNLOAD_URL_EXPIRY):
    return s3_presign_client.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": S3_BUCKET, "Key": s3_key},
        ExpiresIn=expires_in
    )


def generate_download_url(s3_key, expires_in=DOWNLOAD_URL_EXPIRY):
    """Today: S3 pre-signed URL. Future: CloudFront signed URL."""
    return generate_presigned_download_url(s3_key, expires_in)


def delete_s3_object(s3_key):
    try:
        s3_client.delete_object(Bucket=S3_BUCKET, Key=s3_key)
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code in ["NoSuchKey", "404"]:
            log("INFO", "S3 object not found (idempotent)", s3_key=s3_key)
            return
        log("ERROR", "S3 delete failed", s3_key=s3_key, error=str(e))
        raise


def head_object_safe(s3_key):
    try:
        return s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
    except ClientError as e:
        if e.response["Error"]["Code"] in ["404", "NoSuchKey"]:
            return None
        raise
