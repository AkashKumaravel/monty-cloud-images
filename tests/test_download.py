import json
from unittest.mock import patch
from conftest import apigw_event, seed_image


def test_download_success(aws):
    from handlers.download_handler import handler
    seed_image(aws["table"])
    resp = handler(apigw_event(path_params={"image_id": "img-1"}, headers={"x-user-id": "user-1"}), None)
    body = json.loads(resp["body"])
    assert resp["statusCode"] == 200
    assert "download_url" in body
    assert body["image_id"] == "img-1"
    assert body["expires_in"] == 3600


def test_download_missing_auth(aws):
    from handlers.download_handler import handler
    resp = handler(apigw_event(path_params={"image_id": "img-1"}), None)
    assert resp["statusCode"] == 401


def test_download_missing_image_id(aws):
    from handlers.download_handler import handler
    resp = handler(apigw_event(path_params={}, headers={"x-user-id": "user-1"}), None)
    assert resp["statusCode"] == 400


def test_download_not_found(aws):
    from handlers.download_handler import handler
    resp = handler(apigw_event(path_params={"image_id": "nonexistent"}, headers={"x-user-id": "user-1"}), None)
    assert resp["statusCode"] == 404


def test_download_forbidden(aws):
    from handlers.download_handler import handler
    seed_image(aws["table"], user_id="owner-1")
    resp = handler(apigw_event(path_params={"image_id": "img-1"}, headers={"x-user-id": "other-user"}), None)
    assert resp["statusCode"] == 403


def test_download_case_insensitive_header(aws):
    from handlers.download_handler import handler
    seed_image(aws["table"])
    resp = handler(apigw_event(path_params={"image_id": "img-1"}, headers={"X-User-Id": "user-1"}), None)
    assert resp["statusCode"] == 200


def test_download_null_path_params(aws):
    from handlers.download_handler import handler
    resp = handler(apigw_event(headers={"x-user-id": "user-1"}), None)
    assert resp["statusCode"] == 400


def test_download_internal_error(aws):
    from handlers.download_handler import handler
    with patch("handlers.download_handler.get_image_metadata", side_effect=Exception("db down")):
        resp = handler(apigw_event(path_params={"image_id": "img-1"}, headers={"x-user-id": "user-1"}), None)
        assert resp["statusCode"] == 500
