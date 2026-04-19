import os


def get_env_variable(name, required=True, default=None):
    value = os.getenv(name, default)
    if required and value is None:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


LOCALSTACK_ENDPOINT = None
DYNAMODB_TABLE = None
S3_BUCKET = None
DELETE_QUEUE_URL = None
S3_PRESIGN_ENDPOINT = None
_config_error = None

try:
    LOCALSTACK_ENDPOINT = get_env_variable("LOCALSTACK_ENDPOINT")
    DYNAMODB_TABLE = get_env_variable("DYNAMODB_TABLE")
    S3_BUCKET = get_env_variable("S3_BUCKET")
    DELETE_QUEUE_URL = get_env_variable("DELETE_QUEUE_URL")
    S3_PRESIGN_ENDPOINT = get_env_variable("S3_PRESIGN_ENDPOINT", required=False, default=LOCALSTACK_ENDPOINT)
except ValueError as e:
    _config_error = str(e)


def validate_config():
    if _config_error:
        raise ValueError(_config_error)
