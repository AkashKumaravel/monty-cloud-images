import time
from layer.python.config import validate_config
from layer.python.s3_service import generate_presigned_upload_url
from layer.python.db_service import create_image_metadata
from layer.python.utils import generate_image_id, get_user_id, parse_body, success, error, log


def handler(event, context):
    try:
        validate_config()

        user_id = get_user_id(event)
        if not user_id:
            return error("Unauthorized", 401)

        body = parse_body(event)
        file_name = body.get("file_name")
        tags = body.get("tags", [])

        if not file_name:
            return error("file_name required")

        image_id = generate_image_id()
        upload_url, s3_key = generate_presigned_upload_url(image_id, file_name)

        current_time = int(time.time())
        uploaded_date = time.strftime("%Y-%m-%d", time.gmtime(current_time))

        create_image_metadata(
            image_id=image_id,
            user_id=user_id,
            file_name=file_name,
            s3_key=s3_key,
            tags=tags,
            status="PENDING",
            uploaded_at=current_time,
            uploaded_date=uploaded_date
        )

        log("INFO", "Created PENDING metadata", image_id=image_id, user_id=user_id)

        return success({
            "image_id": image_id,
            "upload_url": upload_url,
            "s3_key": s3_key,
            "status": "PENDING"
        })

    except ValueError as e:
        log("ERROR", "Upload handler failed", error=str(e))
        return error(str(e), 500)
    except Exception as e:
        log("ERROR", "Upload handler failed", error=str(e))
        return error("Internal Server Error", 500)
