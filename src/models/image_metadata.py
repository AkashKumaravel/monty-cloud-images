"""
DynamoDB schema definition for the image metadata table.

Table: monty-cloud-image-metadata
Billing: PAY_PER_REQUEST
"""

from dataclasses import dataclass, field
from typing import List, Optional


# Table & index names
TABLE_NAME = "monty-cloud-image-metadata"
USER_INDEX = "user-index"
FILE_NAME_INDEX = "file-name-index"

# Key schema
PARTITION_KEY = "image_id"  # String

# GSI definitions
GSI_DEFINITIONS = {
    USER_INDEX: {
        "partition_key": "user_id",   # String
        "sort_key": "uploaded_at",    # Number (epoch)
        "projection": "ALL",
    },
    FILE_NAME_INDEX: {
        "partition_key": "file_name",  # String
        "sort_key": None,
        "projection": "ALL",
    },
}

# Valid status values
STATUS_PENDING = "PENDING"
STATUS_COMPLETED = "COMPLETED"


@dataclass
class ImageMetadata:
    image_id: str
    user_id: str
    file_name: str
    s3_key: str
    status: str = STATUS_PENDING
    tags: List[str] = field(default_factory=list)
    uploaded_at: Optional[int] = None
    uploaded_date: Optional[str] = None

    def to_item(self) -> dict:
        return {
            "image_id": self.image_id,
            "user_id": self.user_id,
            "file_name": self.file_name,
            "s3_key": self.s3_key,
            "status": self.status,
            "tags": self.tags,
            "uploaded_at": self.uploaded_at,
            "uploaded_date": self.uploaded_date,
        }

    @classmethod
    def from_item(cls, item: dict) -> "ImageMetadata":
        return cls(
            image_id=item["image_id"],
            user_id=item["user_id"],
            file_name=item["file_name"],
            s3_key=item["s3_key"],
            status=item.get("status", STATUS_PENDING),
            tags=item.get("tags", []),
            uploaded_at=item.get("uploaded_at"),
            uploaded_date=item.get("uploaded_date"),
        )
