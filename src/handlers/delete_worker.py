import json
from layer.python.s3_service import delete_s3_object
from layer.python.db_service import delete_image_metadata
from layer.python.utils import log


def lambda_handler(event, context):
    for record in event.get("Records", []):
        request_id = None
        user_id = None

        try:
            body = json.loads(record["body"])

            image_id = body["image_id"]
            s3_key = body["s3_key"]
            request_id = body.get("request_id")
            user_id = body.get("user_id")

            # Timeout safety check
            remaining_time = context.get_remaining_time_in_millis()
            if remaining_time < 2000:
                log(
                    "ERROR",
                    "Not enough time to safely process",
                    request_id=request_id,
                    user_id=user_id,
                    image_id=image_id
                )
                raise Exception("Lambda about to timeout")

            log(
                "INFO",
                "Processing delete",
                image_id=image_id,
                request_id=request_id,
                user_id=user_id
            )

            # Step 1: Delete from S3 (idempotent)
            delete_s3_object(s3_key)

            log(
                "INFO",
                "S3 delete completed",
                image_id=image_id,
                request_id=request_id,
                user_id=user_id
            )

            # Step 2: Delete from DynamoDB (idempotent)
            delete_image_metadata(image_id)

            log(
                "INFO",
                "DynamoDB delete completed",
                image_id=image_id,
                request_id=request_id,
                user_id=user_id
            )

            log(
                "INFO",
                "Delete successful",
                image_id=image_id,
                request_id=request_id,
                user_id=user_id
            )

        except Exception as e:
            log(
                "ERROR",
                "Delete worker failed",
                error=str(e),
                request_id=request_id,
                user_id=user_id
            )
            raise e  # triggers retry + DLQ