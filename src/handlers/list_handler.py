import json
import uuid
from layer.python.db_service import (
    query_by_user,
    query_by_file_name,
    scan_images
)
from layer.python.utils import log
from layer.python.pagination import encode_token, decode_token


DEFAULT_LIMIT = 10
MAX_LIMIT = 50


def lambda_handler(event, context):
    request_id = str(uuid.uuid4())

    try:
        query_params = event.get("queryStringParameters") or {}
        headers = event.get("headers") or {}

        # Mock auth (case-insensitive)
        auth_user_id = headers.get("x-user-id") or headers.get("X-User-Id")

        user_id = query_params.get("user_id")
        file_name = query_params.get("file_name")
        tag = query_params.get("tag")
        uploaded_after = query_params.get("uploaded_after")
        uploaded_before = query_params.get("uploaded_before")
        limit = int(query_params.get("limit", DEFAULT_LIMIT))
        next_token = query_params.get("next_token")

        # Validate limit
        if limit > MAX_LIMIT:
            return error_response(400, "InvalidRequest", "Limit cannot exceed 50", request_id)

        # Validate time range
        if uploaded_after and uploaded_before:
            if int(uploaded_after) > int(uploaded_before):
                return error_response(400, "InvalidRequest", "Invalid time range", request_id)

        # Decode pagination token
        exclusive_start_key = decode_token(next_token) if next_token else None

        # Log with auth awareness
        log(
            "INFO",
            "Processing list request",
            request_id=request_id,
            auth_user_id=auth_user_id,
            query_params=query_params
        )

        # Decision logic
        if user_id:
            items, last_evaluated_key = query_by_user(
                user_id=user_id,
                uploaded_after=uploaded_after,
                uploaded_before=uploaded_before,
                limit=limit,
                exclusive_start_key=exclusive_start_key
            )

        elif file_name:
            items, last_evaluated_key = query_by_file_name(
                file_name=file_name,
                limit=limit,
                exclusive_start_key=exclusive_start_key
            )

        elif tag:
            items, last_evaluated_key = scan_images(
                tag=tag,
                limit=limit,
                exclusive_start_key=exclusive_start_key
            )

        else:
            # Full scan
            items, last_evaluated_key = scan_images(
                limit=limit,
                exclusive_start_key=exclusive_start_key
            )

        response = {
            "items": items,
            "count": len(items),
            "request_id": request_id
        }

        if last_evaluated_key:
            response["next_token"] = encode_token(last_evaluated_key)

        return {
            "statusCode": 200,
            "body": json.dumps(response)
        }

    except ValueError:
        # Handles invalid pagination token
        return error_response(400, "InvalidToken", "Invalid pagination token", request_id)

    except Exception as e:
        log("ERROR", "List API failed", error=str(e), request_id=request_id)
        return error_response(500, "InternalError", "Failed to fetch images", request_id)


def error_response(status_code, error, message, request_id):
    return {
        "statusCode": status_code,
        "body": json.dumps({
            "error": error,
            "message": message,
            "request_id": request_id
        })
    }