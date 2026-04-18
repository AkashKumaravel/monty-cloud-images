import json
import uuid
from layer.python.db_service import get_image_metadata
from layer.python.sqs_service import send_delete_message
from layer.python.utils import log


def lambda_handler(event, context):
    request_id = str(uuid.uuid4())

    try:
        path_params = event.get("pathParameters") or {}
        headers = event.get("headers") or {}

        # ✅ Mock auth (case-insensitive)
        auth_user_id = headers.get("x-user-id") or headers.get("X-User-Id")

        image_id = path_params.get("image_id")

        # 🔐 Auth required for delete
        if not auth_user_id:
            return error_response(401, "Unauthorized", "Missing user identity", request_id)

        if not image_id:
            return error_response(400, "InvalidRequest", "image_id is required", request_id)

        log(
            "INFO",
            "Processing delete request",
            image_id=image_id,
            request_id=request_id,
            auth_user_id=auth_user_id
        )

        # Fetch metadata
        item = get_image_metadata(image_id)

        if not item:
            return error_response(404, "NotFound", "Image not found", request_id)

        # 🔐 Ownership validation
        if item.get("user_id") != auth_user_id:
            log(
                "WARNING",
                "Unauthorized delete attempt",
                image_id=image_id,
                request_id=request_id,
                auth_user_id=auth_user_id,
                owner_user_id=item.get("user_id")
            )
            return error_response(403, "Forbidden", "You cannot delete this image", request_id)

        # Prepare async message
        message = {
            "image_id": image_id,
            "s3_key": item["s3_key"],
            "user_id": auth_user_id,
            "request_id": request_id
        }

        send_delete_message(message)

        log(
            "INFO",
            "Delete request queued",
            image_id=image_id,
            request_id=request_id,
            auth_user_id=auth_user_id
        )

        return {
            "statusCode": 202,
            "body": json.dumps({
                "message": "Delete request accepted",
                "image_id": image_id,
                "status": "PENDING",
                "request_id": request_id
            })
        }

    except Exception as e:
        log(
            "ERROR",
            "Delete handler failed",
            error=str(e),
            request_id=request_id
        )
        return error_response(500, "InternalError", "Failed to schedule delete request", request_id)


def error_response(status_code, error, message, request_id):
    return {
        "statusCode": status_code,
        "body": json.dumps({
            "error": error,
            "message": message,
            "request_id": request_id
        })
    }