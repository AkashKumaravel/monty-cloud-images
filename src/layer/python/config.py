import os

def get_env_variable(name: str, required: bool = True, default: str = None) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value

LOCALSTACK_ENDPOINT = get_env_variable("LOCALSTACK_ENDPOINT")
DYNAMODB_TABLE = get_env_variable("DYNAMODB_TABLE")
S3_BUCKET = get_env_variable("S3_BUCKET")
DELETE_QUEUE_URL = get_env_variable("DELETE_QUEUE_URL")
