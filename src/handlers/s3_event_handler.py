from urllib.parse import unquote_plus
from layer.python.db_service import get_image_metadata, update_image_status
from layer.python.utils import log
from models.image_metadata import STATUS_PENDING, STATUS_COMPLETED


def handler(event, context):
    for record in event.get("Records", []):
        try:
            s3 = record["s3"]
            key = unquote_plus(s3["object"]["key"])

            # Parse image_id from s3 key (format: {image_id}_{file_name})
            if "_" not in key:
                log("WARNING", "Unexpected S3 key format", s3_key=key)
                continue

            image_id = key.split("_", 1)[0]

            # Only update existing PENDING records
            existing = get_image_metadata(image_id)
            if not existing:
                log("WARNING", "No metadata found for S3 key", s3_key=key, image_id=image_id)
                continue

            if existing.status != STATUS_PENDING:
                log("INFO", "Already processed", image_id=image_id, status=existing.status)
                continue

            update_image_status(image_id, STATUS_COMPLETED)

            log("INFO", "Marked COMPLETED", image_id=image_id, s3_key=key)

        except Exception as e:
            log("ERROR", "Failed to process S3 event", error=str(e), record=record)
            raise e
