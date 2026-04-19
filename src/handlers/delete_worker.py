import json
from layer.python.s3_service import delete_s3_object
from layer.python.db_service import delete_image_metadata
from layer.python.utils import log


def handler(event, context):
    for record in event.get("Records", []):
        body = json.loads(record["body"])
        image_id = body["image_id"]
        s3_key = body["s3_key"]
        request_id = body.get("request_id")

        try:
            remaining = context.get_remaining_time_in_millis()
            if remaining < 2000:
                raise TimeoutError("Lambda about to timeout")

            log("INFO", "Processing delete", image_id=image_id, request_id=request_id)

            delete_s3_object(s3_key)
            delete_image_metadata(image_id)

            log("INFO", "Delete successful", image_id=image_id, request_id=request_id)

        except Exception as e:
            log("ERROR", "Delete worker failed", image_id=image_id, request_id=request_id, error=str(e))
            raise
