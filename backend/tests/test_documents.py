import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.routes.data import _content_disposition
from app.core.database import get_db
from app.main import app
from app.models.user import User


class DocumentQuery:
    def __init__(self, document=None):
        self.document = document

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return [self.document] if self.document else []

    def first(self):
        return self.document


class DocumentSession:
    def __init__(self, document=None):
        self.document = document

    def query(self, *args, **kwargs):
        return DocumentQuery(self.document)

    def execute(self, statement):
        return 1


def _user() -> User:
    return User(
        id=uuid.uuid4(),
        email="documents@example.com",
        full_name="Documents User",
        password_hash="unused",
        is_active=True,
    )


def test_document_download_filename_is_safe() -> None:
    disposition = _content_disposition('report"\r\nX-Leak: true')

    assert "\r" not in disposition
    assert "\n" not in disposition
    assert "X-Leak:" not in disposition
    assert disposition.endswith(".pdf\"")


def test_document_list_and_download_are_private() -> None:
    user = _user()
    document = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user.id,
        filename="certificate.pdf",
        document_type="certificate",
        mime_type="application/pdf",
        data=b"%PDF-1.7 test",
        created_at=datetime.now(timezone.utc),
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: DocumentSession(document)
    try:
        client = TestClient(app)
        listed = client.get("/api/v1/account/documents")
        assert listed.status_code == 200
        assert listed.json()[0]["size_bytes"] == len(document.data)

        downloaded = client.get(f"/api/v1/account/documents/{document.id}/download")
        assert downloaded.status_code == 200
        assert downloaded.content == document.data
        assert downloaded.headers["cache-control"] == "private, no-store"
    finally:
        app.dependency_overrides.clear()


def test_document_upload_rejects_non_pdf_before_database_write() -> None:
    user = _user()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: DocumentSession()
    try:
        response = TestClient(app).post(
            "/api/v1/account/documents",
            files={"file": ("notes.txt", b"not a pdf", "text/plain")},
        )
        assert response.status_code == 400
        assert response.json()["error"]["message"] == "Only PDF documents are supported"
    finally:
        app.dependency_overrides.clear()


def test_document_download_returns_not_found_for_unknown_document() -> None:
    user = _user()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: DocumentSession()
    try:
        response = TestClient(app).get(f"/api/v1/account/documents/{uuid.uuid4()}")
        assert response.status_code == 404
        assert response.json()["error"]["message"] == "Document not found"
    finally:
        app.dependency_overrides.clear()


def test_health_readiness_and_request_id() -> None:
    app.dependency_overrides[get_db] = lambda: DocumentSession()
    try:
        response = TestClient(app).get(
            "/health/ready", headers={"X-Request-ID": "test-request-id"}
        )
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}
        assert response.headers["x-request-id"] == "test-request-id"
    finally:
        app.dependency_overrides.clear()
