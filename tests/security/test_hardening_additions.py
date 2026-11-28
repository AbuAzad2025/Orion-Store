"""Coverage for the recent security hardening additions."""

from __future__ import annotations

import time
import uuid

import pytest
from cryptography.fernet import Fernet
from itsdangerous import URLSafeSerializer

from core.exceptions import ValidationError
from core.store_token import SALT, _serializer, resolve, signed_url
from engine.schema import product_schema
from v1.product_images import _check_quota


class _Tenant:
    public_id = uuid.uuid4()
    default_currency = "ILS"


class _Product:
    image_url = "/store/static/images/products/demo/a.jpg"
    name = "A"
    quantity = 2
    price = "1.00"


def test_signed_url_replaces_only_store_param() -> None:
    url = "/store/static/images/products/demo/a.jpg?store=old&x=1"
    assert (
        signed_url(url, "new")
        == "/store/static/images/products/demo/a.jpg?x=1&store=new"
    )
    # Never leak the token to an external origin or a non-image local path.
    assert (
        signed_url("https://cdn.example.com/a.jpg", "new")
        == "https://cdn.example.com/a.jpg"
    )
    assert signed_url("/img/a.jpg", "new") == "/img/a.jpg"
    assert signed_url(None, "new") == ""


def test_product_schema_signs_local_image_only(app) -> None:
    tenant = _Tenant()
    with app.app_context():
        schema = product_schema(_Product(), {"name": "A"}, tenant, "tok")
    assert schema["image"] == ["/store/static/images/products/demo/a.jpg?store=tok"]
    product = _Product()
    product.image_url = "https://cdn.example.com/a.jpg"
    with app.app_context():
        schema = product_schema(product, {}, tenant, "tok")
    assert schema["image"] == ["https://cdn.example.com/a.jpg"]


def test_store_token_rejects_legacy_and_expired(app) -> None:
    tenant = _Tenant()
    with app.app_context():
        secret = app.config["SECRET_KEY"]
        legacy = URLSafeSerializer(secret, salt=SALT).dumps(
            {"tid": str(tenant.public_id)}
        )
        assert resolve(legacy) is None
        serializer = _serializer()
        real_time = time.time
        time.time = lambda: real_time() - 800000
        try:
            expired = serializer.dumps({"tid": str(tenant.public_id)})
        finally:
            time.time = real_time
        assert resolve(expired) is None


def test_upload_quota_limits(app, tmp_path) -> None:
    (tmp_path / "a.jpg").write_bytes(b"x" * 10)
    (tmp_path / "b.jpg").write_bytes(b"x" * 10)
    with app.app_context():
        app.config["MAX_IMAGES_PER_TENANT"] = 2
        with pytest.raises(ValidationError):
            _check_quota(tmp_path, 5)
        app.config["MAX_IMAGES_PER_TENANT"] = 200
        app.config["MAX_IMAGE_BYTES_PER_TENANT"] = 25
        with pytest.raises(ValidationError):
            _check_quota(tmp_path, 10)


def test_store_folder_is_outside_source(app, tmp_path) -> None:
    from orion.paths import store_folder

    with app.app_context():
        app.config["PRODUCT_IMAGES_DIR"] = str(tmp_path / "images")
        folder = store_folder("valid-slug")
    assert folder.is_dir()
    assert folder.parent == tmp_path / "images"
