import json
import os
import pytest
from unittest.mock import patch
from botocore.exceptions import ClientError


# ── utils ──

from layer.python.utils import (
    success, error, error_response, log, generate_image_id, current_timestamp,
    current_date, parse_body, get_user_id, get_path_param, get_query_param,
)


def test_success_default_status():
    resp = success({"key": "value"})
    assert resp["statusCode"] == 200
    assert json.loads(resp["body"]) == {"key": "value"}
    assert resp["headers"]["Content-Type"] == "application/json"
    assert resp["headers"]["Access-Control-Allow-Origin"] == "*"


def test_success_custom_status():
    resp = success({"created": True}, status_code=201)
    assert resp["statusCode"] == 201


def test_error_default_status():
    resp = error("bad request")
    assert resp["statusCode"] == 400
    assert json.loads(resp["body"]) == {"error": "bad request"}


def test_error_custom_status():
    resp = error("not found", 404)
    assert resp["statusCode"] == 404


def test_error_response_format():
    resp = error_response(403, "Forbidden", "Access denied", "req-123")
    body = json.loads(resp["body"])
    assert resp["statusCode"] == 403
    assert body["error"] == "Forbidden"
    assert body["message"] == "Access denied"
    assert body["request_id"] == "req-123"


def test_log_outputs_json(capsys):
    log("INFO", "test message", extra="data")
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "test message"
    assert parsed["extra"] == "data"
    assert "timestamp" in parsed


def test_generate_image_id_unique():
    id1 = generate_image_id()
    id2 = generate_image_id()
    assert id1 != id2
    assert len(id1) == 36


def test_current_timestamp():
    ts = current_timestamp()
    assert isinstance(ts, int)
    assert ts > 0


def test_current_date():
    d = current_date()
    assert len(d) == 10
    assert "-" in d


def test_parse_body_valid():
    event = {"body": json.dumps({"key": "val"})}
    assert parse_body(event) == {"key": "val"}


def test_parse_body_none():
    assert parse_body({}) == {}


def test_parse_body_invalid_json():
    assert parse_body({"body": "not-json"}) == {}


def test_get_user_id_lowercase():
    assert get_user_id({"headers": {"x-user-id": "u1"}}) == "u1"


def test_get_user_id_uppercase():
    assert get_user_id({"headers": {"X-User-Id": "u1"}}) == "u1"


def test_get_user_id_missing():
    assert get_user_id({"headers": {}}) is None


def test_get_user_id_no_headers():
    assert get_user_id({}) is None


def test_get_path_param():
    event = {"pathParameters": {"image_id": "abc"}}
    assert get_path_param(event, "image_id") == "abc"


def test_get_path_param_missing():
    assert get_path_param({"pathParameters": {}}, "image_id") is None


def test_get_path_param_none():
    assert get_path_param({"pathParameters": None}, "image_id") is None


def test_get_query_param():
    event = {"queryStringParameters": {"user_id": "u1"}}
    assert get_query_param(event, "user_id") == "u1"


def test_get_query_param_default():
    event = {"queryStringParameters": {}}
    assert get_query_param(event, "missing", "default") == "default"


def test_get_query_param_none_params():
    event = {"queryStringParameters": None}
    assert get_query_param(event, "key") is None


# ── pagination ──

from layer.python.pagination import encode_token, decode_token


def test_encode_decode_token():
    original = {"image_id": "abc", "uploaded_at": 123}
    token = encode_token(original)
    assert isinstance(token, str)
    assert decode_token(token) == original


def test_decode_invalid_token():
    with pytest.raises(ValueError, match="Invalid pagination token"):
        decode_token("!!!not-base64!!!")


def test_decode_non_json_base64():
    import base64
    token = base64.b64encode(b"not-json").decode()
    with pytest.raises(ValueError, match="Invalid pagination token"):
        decode_token(token)


# ── config ──

def test_config_get_env_variable_required_missing():
    from layer.python.config import get_env_variable
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("NONEXISTENT_VAR", None)
        with pytest.raises(ValueError, match="Missing required environment variable"):
            get_env_variable("NONEXISTENT_VAR")


def test_config_get_env_variable_optional():
    from layer.python.config import get_env_variable
    result = get_env_variable("NONEXISTENT_VAR", required=False, default="fallback")
    assert result == "fallback"


def test_config_get_env_variable_exists():
    from layer.python.config import get_env_variable
    with patch.dict(os.environ, {"MY_VAR": "hello"}):
        assert get_env_variable("MY_VAR") == "hello"


# ── db_service ──

def test_db_get_image_metadata(aws):
    from layer.python.db_service import get_image_metadata
    aws["table"].put_item(Item={"image_id": "t1", "user_id": "u1", "s3_key": "k", "file_name": "f.jpg", "uploaded_at": 100, "tags": []})
    item = get_image_metadata("t1")
    assert item.user_id == "u1"


def test_db_get_image_metadata_not_found(aws):
    from layer.python.db_service import get_image_metadata
    assert get_image_metadata("nonexistent") is None


def test_db_delete_image_metadata(aws):
    from layer.python.db_service import get_image_metadata, delete_image_metadata
    aws["table"].put_item(Item={"image_id": "del-1", "user_id": "u1", "s3_key": "k", "file_name": "f.jpg", "uploaded_at": 100, "tags": []})
    delete_image_metadata("del-1")
    assert get_image_metadata("del-1") is None


def test_db_create_image_metadata(aws):
    from layer.python.db_service import create_image_metadata, get_image_metadata
    from models.image_metadata import ImageMetadata
    metadata = ImageMetadata(image_id="c1", user_id="u1", file_name="f.jpg", s3_key="c1_f.jpg", tags=["a"], status="PENDING", uploaded_at=100, uploaded_date="2024-01-01")
    create_image_metadata(metadata)
    item = get_image_metadata("c1")
    assert item.status == "PENDING"
    assert item.tags == ["a"]


def test_db_create_image_metadata_default_tags(aws):
    from layer.python.db_service import create_image_metadata, get_image_metadata
    from models.image_metadata import ImageMetadata
    metadata = ImageMetadata(image_id="c2", user_id="u1", file_name="f.jpg", s3_key="c2_f.jpg", uploaded_at=100, uploaded_date="2024-01-01")
    create_image_metadata(metadata)
    item = get_image_metadata("c2")
    assert item.tags == []


def test_db_update_image_status(aws):
    from layer.python.db_service import update_image_status, get_image_metadata
    aws["table"].put_item(Item={"image_id": "upd-1", "user_id": "u1", "s3_key": "k", "file_name": "f.jpg", "uploaded_at": 100, "tags": [], "status": "PENDING"})
    update_image_status("upd-1", "COMPLETED")
    item = get_image_metadata("upd-1")
    assert item.status == "COMPLETED"


def test_db_query_by_user(aws):
    from layer.python.db_service import query_by_user
    aws["table"].put_item(Item={"image_id": "q1", "user_id": "u2", "s3_key": "k1", "file_name": "a.jpg", "uploaded_at": 1000, "tags": []})
    aws["table"].put_item(Item={"image_id": "q2", "user_id": "u2", "s3_key": "k2", "file_name": "b.jpg", "uploaded_at": 2000, "tags": []})
    items, last_key = query_by_user("u2")
    assert len(items) == 2


def test_db_query_by_user_with_after(aws):
    from layer.python.db_service import query_by_user
    aws["table"].put_item(Item={"image_id": "qa1", "user_id": "u3", "s3_key": "k", "file_name": "f.jpg", "uploaded_at": 500, "tags": []})
    aws["table"].put_item(Item={"image_id": "qa2", "user_id": "u3", "s3_key": "k2", "file_name": "f2.jpg", "uploaded_at": 1500, "tags": []})
    items, _ = query_by_user("u3", uploaded_after="1000")
    assert len(items) == 1


def test_db_query_by_user_with_before(aws):
    from layer.python.db_service import query_by_user
    aws["table"].put_item(Item={"image_id": "qb1", "user_id": "u4", "s3_key": "k", "file_name": "f.jpg", "uploaded_at": 500, "tags": []})
    items, _ = query_by_user("u4", uploaded_before="1000")
    assert len(items) == 1


def test_db_query_by_user_with_range(aws):
    from layer.python.db_service import query_by_user
    aws["table"].put_item(Item={"image_id": "qr1", "user_id": "u5", "s3_key": "k", "file_name": "f.jpg", "uploaded_at": 1500, "tags": []})
    items, _ = query_by_user("u5", uploaded_after="1000", uploaded_before="2000")
    assert len(items) == 1


def test_db_query_by_file_name(aws):
    from layer.python.db_service import query_by_file_name
    aws["table"].put_item(Item={"image_id": "fn1", "user_id": "u1", "s3_key": "k", "file_name": "report.pdf", "uploaded_at": 100, "tags": []})
    items, _ = query_by_file_name("report.pdf")
    assert len(items) == 1


def test_db_scan_images(aws):
    from layer.python.db_service import scan_images
    aws["table"].put_item(Item={"image_id": "sc1", "user_id": "u1", "s3_key": "k", "file_name": "f.jpg", "uploaded_at": 100, "tags": ["nature"]})
    items, _ = scan_images()
    assert len(items) >= 1


def test_db_scan_images_with_tag(aws):
    from layer.python.db_service import scan_images
    aws["table"].put_item(Item={"image_id": "st1", "user_id": "u1", "s3_key": "k", "file_name": "f.jpg", "uploaded_at": 100, "tags": ["sunset"]})
    aws["table"].put_item(Item={"image_id": "st2", "user_id": "u1", "s3_key": "k2", "file_name": "f2.jpg", "uploaded_at": 200, "tags": ["city"]})
    items, _ = scan_images(tag="sunset")
    assert all("sunset" in i["tags"] for i in items)


def test_db_image_exists(aws):
    from layer.python.db_service import image_exists
    aws["table"].put_item(Item={"image_id": "ex1", "user_id": "u1", "s3_key": "k", "file_name": "f.jpg", "uploaded_at": 100, "tags": []})
    assert image_exists("ex1") is True
    assert image_exists("nonexistent") is False


def test_db_put_image_metadata_idempotent(aws):
    from layer.python.db_service import put_image_metadata
    from models.image_metadata import ImageMetadata
    metadata = ImageMetadata(image_id="dup-1", user_id="u1", s3_key="k", file_name="f.jpg", uploaded_at=100)
    assert put_image_metadata(metadata) is True
    assert put_image_metadata(metadata) is False


def test_db_put_image_metadata_other_error(aws):
    from layer.python.db_service import put_image_metadata
    from models.image_metadata import ImageMetadata
    with patch("layer.python.db_service.table") as mock_table:
        mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "InternalServerError", "Message": "fail"}}, "PutItem"
        )
        with pytest.raises(ClientError):
            put_image_metadata(ImageMetadata(image_id="err-1", user_id="u", file_name="f", s3_key="k"))


def test_db_delete_stale_pending(aws):
    from layer.python.db_service import delete_stale_pending, get_image_metadata
    aws["table"].put_item(Item={"image_id": "stale-1", "user_id": "u1", "s3_key": "k", "file_name": "f.jpg", "uploaded_at": 1, "tags": [], "status": "PENDING"})
    aws["table"].put_item(Item={"image_id": "fresh-1", "user_id": "u1", "s3_key": "k2", "file_name": "f2.jpg", "uploaded_at": 9999999999, "tags": [], "status": "PENDING"})
    count = delete_stale_pending(max_age_seconds=100)
    assert count >= 1
    assert get_image_metadata("stale-1") is None
    assert get_image_metadata("fresh-1") is not None


# ── s3_service ──

def test_s3_generate_presigned_upload_url(aws):
    from layer.python.s3_service import generate_presigned_upload_url
    url, key = generate_presigned_upload_url("img-1", "photo.jpg")
    assert "img-1_photo.jpg" in url
    assert key == "img-1_photo.jpg"


def test_s3_generate_download_url(aws):
    from layer.python.s3_service import generate_download_url
    url = generate_download_url("some/key.jpg")
    assert "some/key.jpg" in url


def test_s3_generate_presigned_download_url(aws):
    from layer.python.s3_service import generate_presigned_download_url
    url = generate_presigned_download_url("key.jpg", expires_in=600)
    assert "key.jpg" in url


def test_s3_delete_object(aws):
    from layer.python.s3_service import delete_s3_object
    aws["s3"].put_object(Bucket="image-service-bucket", Key="to-delete.jpg", Body=b"x")
    delete_s3_object("to-delete.jpg")
    objs = aws["s3"].list_objects_v2(Bucket="image-service-bucket", Prefix="to-delete.jpg")
    assert objs.get("KeyCount", 0) == 0


def test_s3_delete_nonexistent_object(aws):
    from layer.python.s3_service import delete_s3_object
    delete_s3_object("does-not-exist.jpg")


def test_s3_head_object_safe_exists(aws):
    from layer.python.s3_service import head_object_safe
    aws["s3"].put_object(Bucket="image-service-bucket", Key="exists.jpg", Body=b"data")
    result = head_object_safe("exists.jpg")
    assert result is not None


def test_s3_head_object_safe_not_found(aws):
    from layer.python.s3_service import head_object_safe
    result = head_object_safe("missing.jpg")
    assert result is None


def test_s3_head_object_safe_other_error(aws):
    from layer.python.s3_service import head_object_safe
    with patch("layer.python.s3_service.s3_client") as mock_client:
        mock_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "fail"}}, "HeadObject"
        )
        with pytest.raises(ClientError):
            head_object_safe("key.jpg")


def test_s3_upload_url_error(aws):
    from layer.python.s3_service import generate_presigned_upload_url
    with patch("layer.python.s3_service.s3_presign_client") as mock_client:
        mock_client.generate_presigned_url.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "fail"}}, "GeneratePresignedUrl"
        )
        with pytest.raises(ClientError):
            generate_presigned_upload_url("img", "file.jpg")


# ── sqs_service ──

def test_sqs_send_delete_message(aws):
    from layer.python.sqs_service import send_delete_message
    send_delete_message({"image_id": "img-1", "s3_key": "k"})
    msgs = aws["sqs"].receive_message(QueueUrl=os.environ["DELETE_QUEUE_URL"])
    assert len(msgs.get("Messages", [])) == 1


def test_sqs_send_error(aws):
    from layer.python.sqs_service import send_delete_message
    with patch("layer.python.sqs_service.sqs") as mock_sqs:
        mock_sqs.send_message.side_effect = Exception("sqs down")
        with pytest.raises(Exception, match="sqs down"):
            send_delete_message({"image_id": "img-1"})
