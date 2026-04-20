from layer.python.constants import (
    DOWNLOAD_URL_EXPIRY,
    ERR_UNAUTHORIZED, ERR_INVALID_REQUEST, ERR_NOT_FOUND, ERR_FORBIDDEN, ERR_INTERNAL,
    MSG_MISSING_USER, MSG_MISSING_IMAGE_ID, MSG_IMAGE_NOT_FOUND, MSG_FORBIDDEN_ACCESS, MSG_DOWNLOAD_FAILED,
)
from layer.python.db_service import get_image_metadata
from layer.python.s3_service import generate_download_url
from layer.python.utils import generate_image_id, get_user_id, get_path_param, success, error_response, log


def handler(event, context):
    request_id = generate_image_id()

    try:
        auth_user_id = get_user_id(event)
        image_id = get_path_param(event, "image_id")

        if not auth_user_id:
            return error_response(401, ERR_UNAUTHORIZED, MSG_MISSING_USER, request_id)

        if not image_id:
            return error_response(400, ERR_INVALID_REQUEST, MSG_MISSING_IMAGE_ID, request_id)

        log("INFO", "Processing download request", image_id=image_id, request_id=request_id)

        item = get_image_metadata(image_id)
        if not item:
            return error_response(404, ERR_NOT_FOUND, MSG_IMAGE_NOT_FOUND, request_id)

        if item.user_id != auth_user_id:
            log("WARNING", "Unauthorized download attempt", image_id=image_id, auth_user_id=auth_user_id)
            return error_response(403, ERR_FORBIDDEN, MSG_FORBIDDEN_ACCESS, request_id)

        download_url = generate_download_url(item.s3_key)

        log("INFO", "Download URL generated", image_id=image_id, request_id=request_id)

        return success({
            "image_id": image_id,
            "download_url": download_url,
            "expires_in": DOWNLOAD_URL_EXPIRY,
            "request_id": request_id
        })

    except Exception as e:
        log("ERROR", "Download API failed", error=str(e), request_id=request_id)
        return error_response(500, ERR_INTERNAL, MSG_DOWNLOAD_FAILED, request_id)
