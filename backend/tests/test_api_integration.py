import uuid

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.routes.ai import _ai_limiter
from app.core.database import get_db
from app.main import app
from app.models.profile import Profile
from app.models.user import User


def _user() -> User:
    return User(
        id=uuid.uuid4(),
        email="integration@example.com",
        full_name="Integration User",
        password_hash="unused",
        is_active=True,
    )


class EmptyQuery:
    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return None

    def all(self):
        return []


class EmptySession:
    def query(self, *args, **kwargs):
        return EmptyQuery()


def test_auth_and_profile_require_authentication() -> None:
    client = TestClient(app, raise_server_exceptions=False)

    assert client.get("/api/v1/auth/me").json() == {
        "error": {"code": "http_error", "message": "Authentication required"}
    }
    response = client.get("/api/v1/profile")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "http_error"


def test_ai_rate_limit_returns_standard_error_response() -> None:
    user = _user()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: EmptySession()
    _ai_limiter.reset()
    old_limit = _ai_limiter.limit
    _ai_limiter.limit = 1
    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/api/v1/ai/roadmap")
        assert response.status_code in {500, 503}
        response = client.post("/api/v1/ai/roadmap")
        assert response.status_code == 429
        assert response.headers["retry-after"]
        assert response.json()["error"]["code"] == "rate_limited"
        assert response.json()["error"]["details"]["retry_after"] >= 1
    finally:
        app.dependency_overrides.clear()
        _ai_limiter.limit = old_limit
        _ai_limiter.reset()


def test_profile_put_persists_nested_cv_payload() -> None:
    user = _user()
    session = type("ProfileSession", (), {})()
    session.profile = None

    def get_profile(model, model_id):
        if model is Profile and session.profile and session.profile.user_id == model_id:
            return session.profile
        return None

    session.get = get_profile
    session.add = lambda profile: setattr(session, "profile", profile)
    session.commit = lambda: None

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: session
    client = TestClient(app, raise_server_exceptions=False)

    payload = {
        "summary": "Tôi là một lập trình viên full-stack",
        "skills": ["Python", "FastAPI", "React"],
        "project": {
            "name": "FuturePath",
            "meta": "2025",
            "description": "Xây dựng nền tảng định hướng nghề nghiệp"
        },
        "activity": {
            "name": "Hackathon 2025",
            "description": "Đạt giải nhì"
        },
        "education": {
            "name": "Đại học Bách Khoa",
            "meta": "Khoa CNTT",
            "description": "Ngành Kỹ thuật phần mềm"
        },
        "achievement": {
            "name": "Top 5 sinh viên xuất sắc",
            "description": "Được trao thưởng"
        }
    }

    try:
        response = client.put("/api/v1/profile", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["summary"] == payload["summary"]
        assert body["project"]["name"] == payload["project"]["name"]
        assert body["skills"] == payload["skills"]
        assert session.profile is not None
        assert session.profile.data["summary"] == payload["summary"]
        assert session.profile.data["project"]["description"] == payload["project"]["description"]
    finally:
        app.dependency_overrides.clear()
