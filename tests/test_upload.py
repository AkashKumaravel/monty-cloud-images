import json
import pytest
from conftest import apigw_event, seed_image


# ── upload_handler ──

def test_upload_success(aws):
    from handlers.upload_handler import handler
    event = apigw_event(body={"file_name": "photo.jpg"}, headers={"x-user-id": "user-1"})
    resp = handler(event, None)
    body = json.loads(resp["body"])
    assert resp["statusCode"] == 200
    assert "upload_url" in body
    assert "image_id" in body
    assert "s3_key" in body
    assert body["status"] == "PENDING"


def test_upload_with_tags(aws):
    from handlers.upload_handler import handler
    event = apigw_event(body={"file_name": "cat.png", "tags": ["pets", "cats"]}, headers={"x-user-id": "user-1"})
    resp = handler(event, None)
    assert resp["statusCode"] == 200


def test_upload_missing_auth(aws):
    from handlers.upload_handler import handler
    event = apigw_event(body={"file_name": "photo.jpg"})
    resp = handler(event, None)
    assert resp["statusCode"] == 401


def test_upload_missing_file_name(aws):
    from handlers.upload_handler import handler
    event = apigw_event(body={"other": "data"}, headers={"x-user-id": "user-1"})
    resp = handler(event, None)
    assert resp["statusCode"] == 400


def test_upload_empty_body(aws):
    from handlers.upload_handler import handler
    event = apigw_event(headers={"x-user-id": "user-1"})
    resp = handler(event, None)
    assert resp["statusCode"] == 400


def test_upload_invalid_json_body(aws):
    from handlers.upload_handler import handler
    event = {"body": "not-json", "headers": {"x-user-id": "user-1"}, "pathParameters": None, "queryStringParameters": None}
    resp = handler(event, None)
    assert resp["statusCode"] == 400


# ── s3_event_handler ──

def test_s3_event_marks_completed(aws):
    from handlers.s3_event_handler import handler
    from layer.python.db_service import get_image_metadata
    seed_image(aws["table"], image_id="img-abc", s3_key="img-abc_photo.jpg", status="PENDING")
    event = {"Records": [{"s3": {"object": {"key": "img-abc_photo.jpg"}}}]}
    handler(event, None)
    item = get_image_metadata("img-abc")
    assert item.status == "COMPLETED"


def test_s3_event_skips_already_completed(aws):
    from handlers.s3_event_handler import handler
    from layer.python.db_service import get_image_metadata
    seed_image(aws["table"], image_id="img-done", s3_key="img-done_photo.jpg", status="COMPLETED")
    event = {"Records": [{"s3": {"object": {"key": "img-done_photo.jpg"}}}]}
    handler(event, None)
    item = get_image_metadata("img-done")
    assert item.status == "COMPLETED"


def test_s3_event_skips_no_metadata(aws):
    from handlers.s3_event_handler import handler
    event = {"Records": [{"s3": {"object": {"key": "unknown-id_photo.jpg"}}}]}
    handler(event, None)  # should not raise


def test_s3_event_skips_no_underscore(aws):
    from handlers.s3_event_handler import handler
    event = {"Records": [{"s3": {"object": {"key": "nounderscore.jpg"}}}]}
    handler(event, None)  # should skip gracefully


def test_s3_event_url_encoded_key(aws):
    from handlers.s3_event_handler import handler
    from layer.python.db_service import get_image_metadata
    seed_image(aws["table"], image_id="img-enc", s3_key="img-enc_my photo.jpg", status="PENDING")
    event = {"Records": [{"s3": {"object": {"key": "img-enc_my+photo.jpg"}}}]}
    handler(event, None)
    item = get_image_metadata("img-enc")
    assert item.status == "COMPLETED"


def test_s3_event_empty_records(aws):
    from handlers.s3_event_handler import handler
    handler({"Records": []}, None)


def test_s3_event_bad_record_raises(aws):
    from handlers.s3_event_handler import handler
    with pytest.raises(Exception):
        handler({"Records": [{"bad": "data"}]}, None)
