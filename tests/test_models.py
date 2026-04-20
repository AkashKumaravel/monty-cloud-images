from layer.python.constants import (
    STATUS_PENDING, STATUS_COMPLETED,
    TABLE_NAME, USER_INDEX, FILE_NAME_INDEX,
)
from models.image_metadata import ImageMetadata, PARTITION_KEY


def test_to_item_all_fields():
    m = ImageMetadata(
        image_id="id-1", user_id="u1", file_name="f.jpg", s3_key="id-1_f.jpg",
        status="COMPLETED", tags=["a", "b"], uploaded_at=1000, uploaded_date="2024-01-01",
    )
    item = m.to_item()
    assert item == {
        "image_id": "id-1", "user_id": "u1", "file_name": "f.jpg",
        "s3_key": "id-1_f.jpg", "status": "COMPLETED", "tags": ["a", "b"],
        "uploaded_at": 1000, "uploaded_date": "2024-01-01",
    }


def test_to_item_defaults():
    m = ImageMetadata(image_id="id-2", user_id="u1", file_name="f.jpg", s3_key="k")
    item = m.to_item()
    assert item["status"] == STATUS_PENDING
    assert item["tags"] == []
    assert item["uploaded_at"] is None
    assert item["uploaded_date"] is None


def test_from_item_all_fields():
    item = {
        "image_id": "id-3", "user_id": "u2", "file_name": "pic.png",
        "s3_key": "id-3_pic.png", "status": "COMPLETED", "tags": ["x"],
        "uploaded_at": 2000, "uploaded_date": "2024-06-01",
    }
    m = ImageMetadata.from_item(item)
    assert m.image_id == "id-3"
    assert m.user_id == "u2"
    assert m.status == "COMPLETED"
    assert m.tags == ["x"]
    assert m.uploaded_at == 2000
    assert m.uploaded_date == "2024-06-01"


def test_from_item_missing_optional_fields():
    item = {"image_id": "id-4", "user_id": "u1", "file_name": "f.jpg", "s3_key": "k"}
    m = ImageMetadata.from_item(item)
    assert m.status == STATUS_PENDING
    assert m.tags == []
    assert m.uploaded_at is None
    assert m.uploaded_date is None


def test_round_trip():
    original = ImageMetadata(
        image_id="rt-1", user_id="u1", file_name="f.jpg", s3_key="rt-1_f.jpg",
        status="COMPLETED", tags=["t1"], uploaded_at=500, uploaded_date="2024-03-01",
    )
    rebuilt = ImageMetadata.from_item(original.to_item())
    assert rebuilt == original


def test_constants():
    assert STATUS_PENDING == "PENDING"
    assert STATUS_COMPLETED == "COMPLETED"
    assert TABLE_NAME == "monty-cloud-image-metadata"
    assert USER_INDEX == "user-index"
    assert FILE_NAME_INDEX == "file-name-index"
    assert PARTITION_KEY == "image_id"
