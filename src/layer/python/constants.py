# ── DynamoDB table ──
TABLE_NAME = "monty-cloud-image-metadata"

# ── Status ──
STATUS_PENDING = "PENDING"
STATUS_COMPLETED = "COMPLETED"

# ── DynamoDB indexes ──
USER_INDEX = "user-index"
FILE_NAME_INDEX = "file-name-index"

# ── Pagination ──
DEFAULT_PAGE_LIMIT = 10
MAX_PAGE_LIMIT = 50

# ── Pre-signed URL expiry (seconds) ──
UPLOAD_URL_EXPIRY = 300
DOWNLOAD_URL_EXPIRY = 3600

# ── Cleanup ──
STALE_THRESHOLD_SECONDS = 86400  # 24 hours

# ── Lambda safety ──
TIMEOUT_SAFETY_MARGIN_MS = 2000

# ── Date format ──
DATE_FORMAT = "%Y-%m-%d"

# ── Response headers ──
RESPONSE_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
}

# ── Error codes ──
ERR_UNAUTHORIZED = "Unauthorized"
ERR_INVALID_REQUEST = "InvalidRequest"
ERR_NOT_FOUND = "NotFound"
ERR_FORBIDDEN = "Forbidden"
ERR_INTERNAL = "InternalError"
ERR_INVALID_TOKEN = "InvalidToken"

# ── Error messages ──
MSG_MISSING_USER = "Missing user identity"
MSG_MISSING_IMAGE_ID = "image_id is required"
MSG_IMAGE_NOT_FOUND = "Image not found"
MSG_FORBIDDEN_ACCESS = "You cannot access this image"
MSG_FORBIDDEN_DELETE = "You cannot delete this image"
MSG_LIMIT_EXCEEDED = "Limit cannot exceed 50"
MSG_INVALID_TIME_RANGE = "Invalid time range"
MSG_INVALID_PAGINATION = "Invalid pagination token"
MSG_FILE_NAME_REQUIRED = "file_name required"
MSG_DELETE_ACCEPTED = "Delete request accepted"
MSG_INTERNAL_ERROR = "Internal Server Error"
MSG_FETCH_FAILED = "Failed to fetch images"
MSG_DOWNLOAD_FAILED = "Failed to generate download URL"
MSG_DELETE_FAILED = "Failed to schedule delete request"
