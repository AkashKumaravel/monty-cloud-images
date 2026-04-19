from layer.python.db_service import get_image_metadata
from layer.python.sqs_service import send_delete_message
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

        log("INFO", "Processing delete request", image_id=image_id, request_id=request_id)

        item = get_image_metadata(image_id)
        if not item:
            return error_response(404, "NotFound", "Image not found", request_id)

        if item.get("user_id") != auth_user_id:
            log("WARNING", "Unauthorized delete attempt", image_id=image_id, auth_user_id=auth_user_id)
            return error_response(403, "Forbidden", "You cannot delete this image", request_id)

        send_delete_message({
            "image_id": image_id,
            "s3_key": item["s3_key"],
            "user_id": auth_user_id,
            "request_id": request_id
        })

        log("INFO", "Delete request queued", image_id=image_id, request_id=request_id)

        return success({
            "message": "Delete request accepted",
            "image_id": image_id,
            "status": "PENDING",
            "request_id": request_id
        }, 202)

    except Exception as e:
        log("ERROR", "Delete handler failed", error=str(e), request_id=request_id)
        return error_response(500, "InternalError", "Failed to schedule delete request", request_id)
