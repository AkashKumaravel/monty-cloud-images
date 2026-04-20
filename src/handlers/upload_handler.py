import time
from layer.python.config import validate_config
from layer.python.constants import STATUS_PENDING, DATE_FORMAT, MSG_FILE_NAME_REQUIRED, MSG_INTERNAL_ERROR, ERR_UNAUTHORIZED
from layer.python.s3_service import generate_presigned_upload_url
from layer.python.db_service import create_image_metadata
from layer.python.utils import generate_image_id, get_user_id, parse_body, success, error, log
from models.image_metadata import ImageMetadata


def handler(event, context):
    try:
        validate_config()

        user_id = get_user_id(event)
        if not user_id:
            return error(ERR_UNAUTHORIZED, 401)

        body = parse_body(event)
        file_name = body.get("file_name")
        tags = body.get("tags", [])

        if not file_name:
            return error(MSG_FILE_NAME_REQUIRED)

        image_id = generate_image_id()
        upload_url, s3_key = generate_presigned_upload_url(image_id, file_name)

        current_time = int(time.time())
        uploaded_date = time.strftime(DATE_FORMAT, time.gmtime(current_time))

        metadata = ImageMetadata(
            image_id=image_id,
            user_id=user_id,
            file_name=file_name,
            s3_key=s3_key,
            tags=tags,
            uploaded_at=current_time,
            uploaded_date=uploaded_date,
        )
        create_image_metadata(metadata)

        log("INFO", "Created PENDING metadata", image_id=image_id, user_id=user_id)

        return success({
            "image_id": image_id,
            "upload_url": upload_url,
            "s3_key": s3_key,
            "status": STATUS_PENDING
        })

    except ValueError as e:
        log("ERROR", "Upload handler failed", error=str(e))
        return error(str(e), 500)
    except Exception as e:
        log("ERROR", "Upload handler failed", error=str(e))
        return error(MSG_INTERNAL_ERROR, 500)
