from layer.python.constants import (
    STATUS_PENDING,
    ERR_UNAUTHORIZED, ERR_INVALID_REQUEST, ERR_NOT_FOUND, ERR_FORBIDDEN, ERR_INTERNAL,
    MSG_MISSING_USER, MSG_MISSING_IMAGE_ID, MSG_IMAGE_NOT_FOUND, MSG_FORBIDDEN_DELETE,
    MSG_DELETE_ACCEPTED, MSG_DELETE_FAILED,
)
from layer.python.db_service import get_image_metadata
from layer.python.sqs_service import send_delete_message
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

        log("INFO", "Processing delete request", image_id=image_id, request_id=request_id)

        item = get_image_metadata(image_id)
        if not item:
            return error_response(404, ERR_NOT_FOUND, MSG_IMAGE_NOT_FOUND, request_id)

        if item.user_id != auth_user_id:
            log("WARNING", "Unauthorized delete attempt", image_id=image_id, auth_user_id=auth_user_id)
            return error_response(403, ERR_FORBIDDEN, MSG_FORBIDDEN_DELETE, request_id)

        send_delete_message({
            "image_id": image_id,
            "s3_key": item.s3_key,
            "user_id": auth_user_id,
            "request_id": request_id
        })

        log("INFO", "Delete request queued", image_id=image_id, request_id=request_id)

        return success({
            "message": MSG_DELETE_ACCEPTED,
            "image_id": image_id,
            "status": STATUS_PENDING,
            "request_id": request_id
        }, 202)

    except Exception as e:
        log("ERROR", "Delete handler failed", error=str(e), request_id=request_id)
        return error_response(500, ERR_INTERNAL, MSG_DELETE_FAILED, request_id)
