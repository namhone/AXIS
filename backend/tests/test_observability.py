import asyncio
import logging
import re

from fastapi import Request
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import app


def test_unhandled_error_logs_metadata_without_exception_content(caplog):
    scope = {
        "type": "http", "method": "POST", "path": "/api/v1/profile",
        "headers": [], "query_string": b"", "scheme": "http",
        "server": ("testserver", 80), "client": ("127.0.0.1", 1234),
        "root_path": "", "http_version": "1.1", "asgi": {"version": "3.0"},
    }
    request = Request(scope)
    request.state.request_id = "test-request-id"

    with caplog.at_level(logging.ERROR, logger="axis.api"):
        asyncio.run(app.exception_handlers[Exception](request, RuntimeError("private student score 9.8")))

    assert "private student score 9.8" not in caplog.text
    assert "error_type=RuntimeError" in caplog.text
    assert "request_id=test-request-id" in caplog.text


def test_unsafe_external_request_id_is_replaced():
    app.dependency_overrides[get_db] = lambda: None
    try:
        response = TestClient(app).get("/health", headers={"X-Request-ID": "student@example.com\nsecret"})
        assert response.status_code == 200
        assert re.fullmatch(r"[a-f0-9]{32}", response.headers["x-request-id"])
    finally:
        app.dependency_overrides.clear()
