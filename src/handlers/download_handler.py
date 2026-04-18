import json
import uuid
from db_service import get_image_metadata
from s3_service import generate_download_url
from utils import log

def lambda_handler(event, context):
    request_id = str(uuid.uuid4())

    try:
        path_params = event.get("pathParameters") or {}
        headers = event.get("headers") or {}

        # 🔐 Mock auth (REQUIRED)
        auth_user_id = headers.get("x-user-id") or headers.get("X-User-Id")

        image_id = path_params.get("image_id")

        # Validate auth
        if not auth_user_id:
            return error_response(401, "Unauthorized", "Missing user identity", request_id)

        # Validate input
        if not image_id:
            return error_response(400, "InvalidRequest", "image_id is required", request_id)

        log(
            "INFO",
            "Processing download request",
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
                "Unauthorized download attempt",
                image_id=image_id,
                request_id=request_id,
                auth_user_id=auth_user_id,
                owner_user_id=item.get("user_id")
            )
            return error_response(403, "Forbidden", "You cannot access this image", request_id)

        s3_key = item["s3_key"]

        # Generate download URL (abstracted)
        download_url = generate_download_url(s3_key)

        log(
            "INFO",
            "Download URL generated",
            image_id=image_id,
            request_id=request_id,
            auth_user_id=auth_user_id
        )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "image_id": image_id,
                "download_url": download_url,
                "expires_in": 3600,
                "request_id": request_id
            })
        }

    except Exception as e:
        log(
            "ERROR",
            "Download API failed",
            error=str(e),
            request_id=request_id
        )
        return error_response(500, "InternalError", "Failed to generate download URL", request_id)


def error_response(status_code, error, message, request_id):
    return {
        "statusCode": status_code,
        "body": json.dumps({
            "error": error,
            "message": message,
            "request_id": request_id
        })
    }