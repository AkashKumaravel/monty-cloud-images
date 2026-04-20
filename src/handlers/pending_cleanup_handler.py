from layer.python.constants import STALE_THRESHOLD_SECONDS
from layer.python.db_service import delete_stale_pending
from layer.python.utils import log


def handler(event, context):
    try:
        count = delete_stale_pending(STALE_THRESHOLD_SECONDS)
        log("INFO", "Pending cleanup completed", deleted=count)
        return {"deleted": count}
    except Exception as e:
        log("ERROR", "Pending cleanup failed", error=str(e))
        raise e
