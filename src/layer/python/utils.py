import json
import uuid
import time
from decimal import Decimal
from layer.python.constants import RESPONSE_HEADERS, DATE_FORMAT


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def success(body, status_code=200):
    return _build(status_code, body)


def error(message, status_code=400):
    return _build(status_code, {"error": message})


def error_response(status_code, error, message, request_id):
    return _build(status_code, {
        "error": error,
        "message": message,
        "request_id": request_id
    })


def _build(status_code, body):
    return {
        "statusCode": status_code,
        "headers": RESPONSE_HEADERS,
        "body": json.dumps(body, cls=DecimalEncoder),
    }


def log(level, message, **kwargs):
    print(json.dumps({
        "timestamp": int(time.time()),
        "level": level,
        "message": message,
        **kwargs
    }))


def generate_image_id():
    return str(uuid.uuid4())


def current_timestamp():
    return int(time.time())


def current_date():
    return time.strftime(DATE_FORMAT, time.gmtime())


def parse_body(event):
    try:
        return json.loads(event.get("body", "{}"))
    except Exception:
        return {}


def get_user_id(event):
    headers = event.get("headers") or {}
    return headers.get("x-user-id") or headers.get("X-User-Id")


def get_path_param(event, key):
    return (event.get("pathParameters") or {}).get(key)


def get_query_param(event, key, default=None):
    return (event.get("queryStringParameters") or {}).get(key, default)
