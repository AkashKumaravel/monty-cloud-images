import json
import time

def success(body, status_code=200):
    return _build(status_code, body)

def error(message, status_code=400):
    return _build(status_code, {"error": message})

def _build(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body),
    }

def log(level: str, message: str, **kwargs):
    log_entry = {
        "timestamp": int(time.time()),
        "level": level,
        "message": message,
        **kwargs
    }
    print(json.dumps(log_entry))