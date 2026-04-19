import json
import base64
from conftest import apigw_event, seed_image


def test_list_by_user_id(aws):
    from handlers.list_handler import handler
    seed_image(aws["table"], image_id="img-1", user_id="user-1", uploaded_at=1704067200)
    seed_image(aws["table"], image_id="img-2", user_id="user-1", s3_key="img-2_b.jpg", file_name="b.jpg", uploaded_at=1704153600)
    seed_image(aws["table"], image_id="img-3", user_id="user-2", s3_key="img-3_c.jpg", file_name="c.jpg", uploaded_at=1704067200)

    resp = handler(apigw_event(query_params={"user_id": "user-1"}), None)
    body = json.loads(resp["body"])
    assert resp["statusCode"] == 200
    assert body["count"] == 2


def test_list_by_user_empty(aws):
    from handlers.list_handler import handler
    resp = handler(apigw_event(query_params={"user_id": "nobody"}), None)
    body = json.loads(resp["body"])
    assert body["items"] == []
    assert body["count"] == 0


def test_list_by_file_name(aws):
    from handlers.list_handler import handler
    seed_image(aws["table"], image_id="img-fn1", file_name="report.pdf")
    resp = handler(apigw_event(query_params={"file_name": "report.pdf"}), None)
    body = json.loads(resp["body"])
    assert resp["statusCode"] == 200
    assert body["count"] == 1


def test_list_by_tag(aws):
    from handlers.list_handler import handler
    aws["table"].put_item(Item={"image_id": "tag-1", "user_id": "u1", "s3_key": "k", "file_name": "f.jpg", "uploaded_at": 100, "tags": ["nature"], "status": "COMPLETED"})
    aws["table"].put_item(Item={"image_id": "tag-2", "user_id": "u1", "s3_key": "k2", "file_name": "f2.jpg", "uploaded_at": 200, "tags": ["city"], "status": "COMPLETED"})
    resp = handler(apigw_event(query_params={"tag": "nature"}), None)
    body = json.loads(resp["body"])
    assert resp["statusCode"] == 200
    assert any(i["image_id"] == "tag-1" for i in body["items"])


def test_list_full_scan(aws):
    from handlers.list_handler import handler
    seed_image(aws["table"], image_id="scan-1")
    resp = handler(apigw_event(query_params={}), None)
    body = json.loads(resp["body"])
    assert resp["statusCode"] == 200
    assert body["count"] >= 1


def test_list_limit_exceeded(aws):
    from handlers.list_handler import handler
    resp = handler(apigw_event(query_params={"limit": "100"}), None)
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert body["error"] == "InvalidRequest"


def test_list_invalid_time_range(aws):
    from handlers.list_handler import handler
    resp = handler(apigw_event(query_params={"user_id": "u1", "uploaded_after": "9999", "uploaded_before": "1000"}), None)
    assert resp["statusCode"] == 400


def test_list_with_uploaded_after_only(aws):
    from handlers.list_handler import handler
    seed_image(aws["table"], image_id="after-1", user_id="u-time", uploaded_at=5000)
    resp = handler(apigw_event(query_params={"user_id": "u-time", "uploaded_after": "4000"}), None)
    body = json.loads(resp["body"])
    assert resp["statusCode"] == 200
    assert body["count"] == 1


def test_list_with_uploaded_before_only(aws):
    from handlers.list_handler import handler
    seed_image(aws["table"], image_id="before-1", user_id="u-time2", uploaded_at=1000)
    resp = handler(apigw_event(query_params={"user_id": "u-time2", "uploaded_before": "2000"}), None)
    body = json.loads(resp["body"])
    assert resp["statusCode"] == 200
    assert body["count"] == 1


def test_list_with_uploaded_after_and_before(aws):
    from handlers.list_handler import handler
    seed_image(aws["table"], image_id="range-1", user_id="u-range", uploaded_at=3000)
    resp = handler(apigw_event(query_params={"user_id": "u-range", "uploaded_after": "2000", "uploaded_before": "4000"}), None)
    body = json.loads(resp["body"])
    assert resp["statusCode"] == 200
    assert body["count"] == 1


def test_list_invalid_pagination_token(aws):
    from handlers.list_handler import handler
    resp = handler(apigw_event(query_params={"next_token": "!!!invalid!!!"}), None)
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert body["error"] == "InvalidToken"


def test_list_valid_pagination_token(aws):
    from handlers.list_handler import handler
    token = base64.b64encode(json.dumps({"image_id": "img-1"}).encode()).decode()
    resp = handler(apigw_event(query_params={"next_token": token}), None)
    assert resp["statusCode"] == 200


def test_list_no_query_params_key(aws):
    from handlers.list_handler import handler
    event = {"queryStringParameters": None, "headers": {}, "pathParameters": None, "body": None}
    resp = handler(event, None)
    assert resp["statusCode"] == 200
