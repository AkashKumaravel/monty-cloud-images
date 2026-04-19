import json
import pytest
from unittest.mock import patch
from conftest import apigw_event, seed_image, MockLambdaContext


# ── delete_handler ──

def test_delete_queues_request(aws):
    from handlers.delete_handler import handler
    seed_image(aws["table"])
    resp = handler(apigw_event(path_params={"image_id": "img-1"}, headers={"x-user-id": "user-1"}), None)
    assert resp["statusCode"] == 202
    body = json.loads(resp["body"])
    assert body["status"] == "PENDING"
    assert body["image_id"] == "img-1"


def test_delete_missing_auth(aws):
    from handlers.delete_handler import handler
    resp = handler(apigw_event(path_params={"image_id": "img-1"}), None)
    assert resp["statusCode"] == 401


def test_delete_missing_image_id(aws):
    from handlers.delete_handler import handler
    resp = handler(apigw_event(path_params={}, headers={"x-user-id": "user-1"}), None)
    assert resp["statusCode"] == 400


def test_delete_not_found(aws):
    from handlers.delete_handler import handler
    resp = handler(apigw_event(path_params={"image_id": "nonexistent"}, headers={"x-user-id": "user-1"}), None)
    assert resp["statusCode"] == 404


def test_delete_forbidden(aws):
    from handlers.delete_handler import handler
    seed_image(aws["table"], user_id="owner-1")
    resp = handler(apigw_event(path_params={"image_id": "img-1"}, headers={"x-user-id": "other-user"}), None)
    assert resp["statusCode"] == 403


def test_delete_case_insensitive_header(aws):
    from handlers.delete_handler import handler
    seed_image(aws["table"])
    resp = handler(apigw_event(path_params={"image_id": "img-1"}, headers={"X-User-Id": "user-1"}), None)
    assert resp["statusCode"] == 202


def test_delete_null_path_params(aws):
    from handlers.delete_handler import handler
    resp = handler(apigw_event(headers={"x-user-id": "user-1"}), None)
    assert resp["statusCode"] == 400


def test_delete_internal_error(aws):
    from handlers.delete_handler import handler
    with patch("handlers.delete_handler.get_image_metadata", side_effect=Exception("db down")):
        resp = handler(apigw_event(path_params={"image_id": "img-1"}, headers={"x-user-id": "user-1"}), None)
        assert resp["statusCode"] == 500


# ── delete_worker ──

def test_worker_deletes_s3_and_db(aws):
    from handlers.delete_worker import handler
    from layer.python.db_service import get_image_metadata
    seed_image(aws["table"])
    aws["s3"].put_object(Bucket="image-service-bucket", Key="img-1_photo.jpg", Body=b"data")

    sqs_event = {"Records": [{"body": json.dumps({"image_id": "img-1", "s3_key": "img-1_photo.jpg", "user_id": "user-1", "request_id": "req-1"})}]}
    handler(sqs_event, MockLambdaContext())

    assert get_image_metadata("img-1") is None
    objs = aws["s3"].list_objects_v2(Bucket="image-service-bucket", Prefix="img-1_photo.jpg")
    assert objs.get("KeyCount", 0) == 0


def test_worker_timeout_safety(aws):
    from handlers.delete_worker import handler
    seed_image(aws["table"])
    sqs_event = {"Records": [{"body": json.dumps({"image_id": "img-1", "s3_key": "img-1_photo.jpg", "user_id": "user-1"})}]}
    with pytest.raises(TimeoutError):
        handler(sqs_event, MockLambdaContext(remaining_millis=1000))


def test_worker_empty_records(aws):
    from handlers.delete_worker import handler
    handler({"Records": []}, MockLambdaContext())


def test_worker_bad_record_raises(aws):
    from handlers.delete_worker import handler
    sqs_event = {"Records": [{"body": "not-json"}]}
    with pytest.raises(Exception):
        handler(sqs_event, MockLambdaContext())


def test_worker_idempotent_s3_delete(aws):
    from handlers.delete_worker import handler
    seed_image(aws["table"])
    sqs_event = {"Records": [{"body": json.dumps({"image_id": "img-1", "s3_key": "img-1_photo.jpg", "user_id": "user-1"})}]}
    handler(sqs_event, MockLambdaContext())
