import base64
import json


def encode_token(last_evaluated_key: dict) -> str:
    return base64.b64encode(json.dumps(last_evaluated_key).encode()).decode()


def decode_token(token: str) -> dict:
    try:
        return json.loads(base64.b64decode(token).decode())
    except Exception:
        raise ValueError("Invalid pagination token")