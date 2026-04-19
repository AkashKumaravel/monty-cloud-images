from layer.python.db_service import query_by_user, query_by_file_name, scan_images
from layer.python.pagination import encode_token, decode_token
from layer.python.utils import generate_image_id, get_user_id, get_query_param, success, error_response, log

DEFAULT_LIMIT = 10
MAX_LIMIT = 50


def handler(event, context):
    request_id = generate_image_id()

    try:
        query_params = event.get("queryStringParameters") or {}
        user_id = query_params.get("user_id")
        file_name = query_params.get("file_name")
        tag = query_params.get("tag")
        uploaded_after = query_params.get("uploaded_after")
        uploaded_before = query_params.get("uploaded_before")
        limit = int(query_params.get("limit", DEFAULT_LIMIT))
        next_token = query_params.get("next_token")

        if limit > MAX_LIMIT:
            return error_response(400, "InvalidRequest", "Limit cannot exceed 50", request_id)

        if uploaded_after and uploaded_before and int(uploaded_after) > int(uploaded_before):
            return error_response(400, "InvalidRequest", "Invalid time range", request_id)

        exclusive_start_key = decode_token(next_token) if next_token else None

        log("INFO", "Processing list request", request_id=request_id, query_params=query_params)

        if user_id:
            items, last_key = query_by_user(user_id, uploaded_after, uploaded_before, limit, exclusive_start_key)
        elif file_name:
            items, last_key = query_by_file_name(file_name, limit, exclusive_start_key)
        else:
            items, last_key = scan_images(tag, limit, exclusive_start_key)

        response = {"items": items, "count": len(items), "request_id": request_id}
        if last_key:
            response["next_token"] = encode_token(last_key)

        return success(response)

    except ValueError:
        return error_response(400, "InvalidToken", "Invalid pagination token", request_id)
    except Exception as e:
        log("ERROR", "List API failed", error=str(e), request_id=request_id)
        return error_response(500, "InternalError", "Failed to fetch images", request_id)
