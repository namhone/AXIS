import uuid
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.routes import ai as ai_routes
from app.api.routes import auth as auth_routes
from app.api.routes.ai import _ai_limiter, _cv_ai_limiter
from app.core.database import get_db
from app.main import app
from app.models.profile import Profile
from app.models.learning import Assessment, Goal
from app.models.user import User
from app.services.ai import AIService


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


def test_login_failures_are_rate_limited_before_password_verification(monkeypatch) -> None:
    import hashlib

    email = "limited@example.com"
    key = hashlib.sha256(email.encode()).hexdigest()
    old_limit = auth_routes._login_limiter.limit
    auth_routes._login_limiter.reset(key)
    auth_routes._login_limiter.limit = 1
    app.dependency_overrides[get_db] = lambda: EmptySession()
    monkeypatch.setattr(auth_routes, "authenticate_user", lambda *args: None)
    try:
        client = TestClient(app, raise_server_exceptions=False)
        payload = {"email": email, "password": "wrong-password"}
        first = client.post("/api/v1/auth/login", json=payload)
        second = client.post("/api/v1/auth/login", json=payload)
        assert first.status_code == 401
        assert second.status_code == 429
        assert second.headers["retry-after"]
        assert second.json()["error"]["code"] == "rate_limited"
    finally:
        app.dependency_overrides.clear()
        auth_routes._login_limiter.limit = old_limit
        auth_routes._login_limiter.reset(key)


def test_local_live_server_can_complete_cors_preflight() -> None:
    origin = "http://127.0.0.1:5501"
    client = TestClient(app, raise_server_exceptions=False)

    response = client.options(
        "/api/v1/auth/me",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"

    patch_response = client.options(
        "/api/v1/tasks/00000000-0000-0000-0000-000000000001/status",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert patch_response.status_code == 200
    assert "PATCH" in patch_response.headers["access-control-allow-methods"]


def test_ai_rate_limit_returns_standard_error_response(monkeypatch) -> None:
    user = _user()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: EmptySession()

    def unavailable(self, **kwargs):
        raise RuntimeError("AI service unavailable")

    monkeypatch.setattr(AIService, "generate_roadmap", unavailable)
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


def test_cv_ai_locks_after_five_requests_for_ten_minutes(monkeypatch) -> None:
    user = _user()
    app.dependency_overrides[get_current_user] = lambda: user
    monkeypatch.setattr(AIService, "generate_cv", lambda self, cv_data, language, operation: cv_data)
    _cv_ai_limiter.reset()
    client = TestClient(app, raise_server_exceptions=False)
    payload = {"data": {"summary": "CV"}, "language": "vi", "operation": "normalize"}

    try:
        for _ in range(5):
            response = client.post("/api/v1/ai/cv", json=payload)
            assert response.status_code == 200

        response = client.post("/api/v1/ai/cv", json=payload)
        assert response.status_code == 429
        assert response.headers["retry-after"] == "600"
        assert response.json()["error"]["code"] == "rate_limited"
        assert response.json()["error"]["details"]["retry_after"] == 600
    finally:
        app.dependency_overrides.clear()
        _cv_ai_limiter.reset()


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
            "name": "AXIS",
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

        textarea_response = client.put(
            "/api/v1/profile",
            json={
                "interests": "lập trình, dữ liệu\nthiết kế",
                "skills": "Python; SQL",
                "certificates": "IELTS 6.5, MOS",
            },
        )
        assert textarea_response.status_code == 200
        textarea_body = textarea_response.json()
        assert textarea_body["interests"] == ["lập trình", "dữ liệu", "thiết kế"]
        assert textarea_body["skills"] == ["Python", "SQL"]
        assert textarea_body["certificates"] == ["IELTS 6.5", "MOS"]

        subject_response = client.put("/api/v1/profile", json={"subject": "A01"})
        assert subject_response.status_code == 200
        skills_response = client.put("/api/v1/profile", json={"skills": ["Python"]})
        assert skills_response.status_code == 200
        assert skills_response.json()["subject"] == "A01"
        assert session.profile.subject == "A01"
    finally:
        app.dependency_overrides.clear()


def test_profile_provenance_is_derived_from_persistent_user_marker() -> None:
    user = _user()
    user.is_synthetic = True
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

    try:
        get_response = client.get("/api/v1/profile")
        assert get_response.status_code == 200
        assert get_response.json()["dataProvenance"] == "Synthetic"

        update_response = client.put(
            "/api/v1/profile",
            json={"dataProvenance": "Existing", "interests": ["thử nghiệm"]},
        )
        assert update_response.status_code == 200
        assert update_response.json()["dataProvenance"] == "Synthetic"
        assert session.profile.data["dataProvenance"] == "Synthetic"
    finally:
        app.dependency_overrides.clear()


def test_skill_plan_returns_ranked_careers_and_saved_career_goals() -> None:
    user = _user()
    recommendations = [
        {"code": "N01", "name": "Công nghệ thông tin", "score": 92.5},
        {"code": "N06", "name": "Kỹ thuật", "score": 88.0},
        {"code": "N03", "name": "Y dược", "score": 77.25},
    ]
    career_goals = [
        SimpleNamespace(
            category="career",
            title="Tìm hiểu nghề: Thiết kế đồ họa",
            status="pending",
            note="Kỹ năng gợi ý: tư duy thị giác __axis_career_code:N10__",
        ),
        SimpleNamespace(
            category="career",
            title="Tìm hiểu nghề: Tâm lý học",
            status="pending",
            note="Kỹ năng gợi ý: lắng nghe __axis_career_code:N12__",
        ),
    ]

    class AssessmentQuery(EmptyQuery):
        def first(self):
            return SimpleNamespace(
                score_json={"top3": recommendations},
                career_suggestions_json={"top5": recommendations},
            )

    class SkillPlanSession:
        profile = None

        def get(self, model, user_id):
            if model is Profile:
                return self.profile
            return None

        def query(self, model):
            if model is Assessment:
                return AssessmentQuery()
            if model is Goal:
                return type("GoalQuery", (EmptyQuery,), {"all": lambda self: career_goals})()
            return EmptyQuery()

        def add(self, profile):
            self.profile = profile

        def commit(self):
            pass

    session = SkillPlanSession()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: session
    client = TestClient(app, raise_server_exceptions=False)
    try:
        response = client.get("/api/v1/skill-plan")
        assert response.status_code == 200
        assert response.json()["career_focus"]["recommended"] == recommendations
        assert response.json()["career_focus"]["selected"] == [
            {"code": "N10", "name": "Thiết kế đồ họa", "status": "pending", "note": "Kỹ năng gợi ý: tư duy thị giác"},
            {"code": "N12", "name": "Tâm lý học", "status": "pending", "note": "Kỹ năng gợi ý: lắng nghe"},
        ]
    finally:
        app.dependency_overrides.clear()


def test_ai_roadmap_receives_assessment_top_three_and_saved_career_goals(monkeypatch) -> None:
    user = _user()
    top_three = [
        {"code": "N01", "name": "Công nghệ thông tin", "score": 92.5},
        {"code": "N06", "name": "Kỹ thuật", "score": 88.0},
        {"code": "N03", "name": "Y dược", "score": 77.25},
    ]
    profile = Profile(
        user_id=user.id,
        data={},
    )
    career_goals = [
        SimpleNamespace(category="career", title="Tìm hiểu nghề: Thiết kế đồ họa", status="pending",
                        target_date=None, minutes_per_day=30,
                        note="Kỹ năng gợi ý: tư duy thị giác __axis_career_code:N10__"),
        SimpleNamespace(category="career", title="Tìm hiểu nghề: Tâm lý học", status="pending",
                        target_date=None, minutes_per_day=30,
                        note="Kỹ năng gợi ý: lắng nghe __axis_career_code:N12__"),
    ]
    assessment = SimpleNamespace(
        score_json={"top3": top_three},
        career_suggestions_json={"top5": top_three},
    )
    captured = {}

    class Query(EmptyQuery):
        def __init__(self, model):
            self.model = model

        def first(self):
            if self.model is Profile:
                return profile
            if self.model is Assessment:
                return assessment
            return None

        def delete(self, **kwargs):
            return 0

        def all(self):
            return career_goals if self.model is Goal else []

    class RoadmapSession:
        def query(self, model):
            return Query(model)

        def add_all(self, items):
            for item in items:
                if item.id is None:
                    item.id = uuid.uuid4()

        def commit(self):
            pass

        def refresh(self, item):
            pass

        def rollback(self):
            pass

    def capture_prompt(self, *, profile, goals):
        captured["profile"] = profile
        captured["goals"] = goals
        return []

    monkeypatch.setattr(AIService, "generate_roadmap", capture_prompt)
    monkeypatch.setattr(
        ai_routes,
        "normalize_week",
        lambda *args, **kwargs: [
            {"step_number": 1, "title": "Tuần 1", "content": '{"date":"2026-09-29","tasks":[]}'}
        ],
    )
    _ai_limiter.reset()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: RoadmapSession()
    client = TestClient(app, raise_server_exceptions=False)
    try:
        response = client.post("/api/v1/ai/roadmap")
        assert response.status_code == 200
        assert captured["profile"]["career_matches"] == top_three
        assert captured["profile"]["career_focus"]["recommended"] == top_three
        assert captured["profile"]["career_focus"]["selected"] == [
            {"code": "N10", "name": "Thiết kế đồ họa", "status": "pending", "note": "Kỹ năng gợi ý: tư duy thị giác"},
            {"code": "N12", "name": "Tâm lý học", "status": "pending", "note": "Kỹ năng gợi ý: lắng nghe"},
        ]
    finally:
        app.dependency_overrides.clear()
        _ai_limiter.reset()


def test_career_goal_creation_stops_at_two_saved_careers() -> None:
    user = _user()
    existing_goals = [
        SimpleNamespace(note="__axis_career_code:N10__", status="pending"),
        SimpleNamespace(note="__axis_career_code:N12__", status="pending"),
    ]

    class CareerGoalsQuery(EmptyQuery):
        def all(self):
            return existing_goals

    class GoalSession:
        def query(self, model):
            return CareerGoalsQuery()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: GoalSession()
    client = TestClient(app, raise_server_exceptions=False)
    try:
        response = client.post(
            "/api/v1/goals",
            json={
                "title": "Tìm hiểu nghề: Khoa học dữ liệu",
                "status": "pending",
                "category": "career",
                "career_code": "N11",
            },
        )
        assert response.status_code == 409
        assert response.json()["error"]["message"] == "Bạn chỉ có thể thêm tối đa 2 ngành vào lộ trình."
    finally:
        app.dependency_overrides.clear()
