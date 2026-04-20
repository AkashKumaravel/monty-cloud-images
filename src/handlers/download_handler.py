from layer.python.db_service import get_image_metadata
from layer.python.s3_service import generate_download_url
from layer.python.utils import generate_image_id, get_user_id, get_path_param, success, error_response, log


def handler(event, context):
    request_id = generate_image_id()

    try:
        auth_user_id = get_user_id(event)
        image_id = get_path_param(event, "image_id")

        if not auth_user_id:
            return error_response(401, "Unauthorized", "Missing user identity", request_id)

        if not image_id:
            return error_response(400, "InvalidRequest", "image_id is required", request_id)

        log("INFO", "Processing download request", image_id=image_id, request_id=request_id)

        item = get_image_metadata(image_id)
        if not item:
            return error_response(404, "NotFound", "Image not found", request_id)

        if item.user_id != auth_user_id:
            log("WARNING", "Unauthorized download attempt", image_id=image_id, auth_user_id=auth_user_id)
            return error_response(403, "Forbidden", "You cannot access this image", request_id)

        download_url = generate_download_url(item.s3_key)

        log("INFO", "Download URL generated", image_id=image_id, request_id=request_id)

        return success({
            "image_id": image_id,
            "download_url": download_url,
            "expires_in": 3600,
            "request_id": request_id
        })

    except Exception as e:
        log("ERROR", "Download API failed", error=str(e), request_id=request_id)
        return error_response(500, "InternalError", "Failed to generate download URL", request_id)
