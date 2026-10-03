import json
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.deps import get_current_user
from app.api.routes.ai import RiasecEvaluationRequest, _ai_limiter
from app.core.config import Settings
from app.main import app
from app.models.user import User
from app.services.ai import AIService


def _payload() -> dict:
    codes = ("R", "I", "A", "S", "E", "C")
    aspects = {str(index): 70 for index in range(1, 6)}
    answered = {str(index): 2 for index in range(1, 6)}
    return {
        "scores": {"R": 95, "I": 90, "A": 80, "S": 70, "E": 60, "C": 50},
        "aspect_scores": {code: dict(aspects) for code in codes},
        "aspect_answered": {code: dict(answered) for code in codes},
        "completion": 100,
    }


def test_riasec_evaluation_derives_holland_code_and_returns_three_sentences(monkeypatch) -> None:
    user = User(
        id=uuid.uuid4(),
        email="riasec@example.com",
        full_name="RIASEC User",
        password_hash="unused",
        is_active=True,
    )
    captured = {}

    def evaluate(self, **kwargs):
        captured.update(kwargs)
        return {"overall": "Tổng quan.", "direction": "Định hướng.", "summary": "Tóm tắt."}

    monkeypatch.setattr(AIService, "evaluate_riasec", evaluate)
    app.dependency_overrides[get_current_user] = lambda: user
    _ai_limiter.reset()
    client = TestClient(app)
    try:
        response = client.post("/api/v1/ai/riasec-evaluation", json=_payload())
        assert response.status_code == 200
        assert response.json() == {
            "overall": "Tổng quan.",
            "direction": "Định hướng.",
            "summary": "Tóm tắt.",
        }
        assert captured["holland_code"] == "RIA"
        assert captured["aspect_scores"]["R"]["1"] == 70
    finally:
        app.dependency_overrides.clear()
        _ai_limiter.reset()


def test_riasec_evaluation_rejects_missing_aspect_scores() -> None:
    payload = _payload()
    del payload["aspect_scores"]["R"]["5"]
    with pytest.raises(ValidationError):
        RiasecEvaluationRequest.model_validate(payload)

def test_riasec_evaluation_rejects_completion_inconsistent_with_answer_counts() -> None:
    payload = _payload()
    for code in payload["aspect_answered"]:
        payload["aspect_answered"][code] = {str(index): 0 for index in range(1, 6)}

    with pytest.raises(ValidationError, match="completion does not match answered counts"):
        RiasecEvaluationRequest.model_validate(payload)


def test_ai_service_accepts_only_three_single_sentence_fields() -> None:
    service = AIService(Settings(groq_api_key="test"))
    contents = [
        {"overall": "Tổng quan.", "direction": "Định hướng.", "summary": "Tóm tắt."},
        {"overall": "Câu một. Câu hai.", "direction": "Định hướng.", "summary": "Tóm tắt."},
    ]

    class FakeCompletions:
        def create(self, **kwargs):
            content = json.dumps(contents.pop(0), ensure_ascii=False)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
            )

    service._client = SimpleNamespace(
        chat=SimpleNamespace(completions=FakeCompletions())
    )
    arguments = {
        "scores": {"R": 80, "I": 70, "A": 60, "S": 50, "E": 40, "C": 30},
        "aspect_scores": {code: {str(index): 70 for index in range(1, 6)} for code in "RIASEC"},
        "aspect_answered": {code: {str(index): 2 for index in range(1, 6)} for code in "RIASEC"},
        "holland_code": "RIA",
        "completion": 100,
    }

    result = service.evaluate_riasec(**arguments)
    assert set(result) == {"overall", "direction", "summary"}
    with pytest.raises(ValueError, match="invalid RIASEC evaluation text"):
        service.evaluate_riasec(**arguments)
