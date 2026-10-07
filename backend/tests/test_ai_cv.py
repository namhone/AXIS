import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import Mock

from app.api.routes.ai import CVRequest
from app.core.config import Settings
from app.core import rate_limit
from app.core.rate_limit import AuthenticationFailureRateLimiter, LockoutRateLimiter, SlidingWindowRateLimiter
from app.services.ai import AIService


def test_cv_request_accepts_translation_payload():
    request = CVRequest(data={"summary": "Học sinh yêu thích dữ liệu"}, language="en")

    assert request.operation == "translate"
    assert request.data["summary"]


def test_cv_request_rejects_unsupported_language():
    with pytest.raises(ValidationError):
        CVRequest(data={"summary": "text"}, language="fr")


def test_cv_request_rejects_oversized_content():
    with pytest.raises(ValidationError):
        CVRequest(data={"summary": "x" * 16000}, language="en")


def test_cv_fallback_without_provider_key_translates_content():
    service = AIService(Settings(groq_api_key="", groq_model="test-model"))
    result = service.generate_cv({"summary": "Học sinh yêu thích dữ liệu"}, "en", "translate")

    assert result["summary"] == "student yêu thích dữ liệu"


def test_cv_fallback_without_provider_key_normalizes_content():
    service = AIService(Settings(groq_api_key="", groq_model="test-model"))
    result = service.generate_cv({"summary": "  Học sinh   yêu thích  dữ liệu  "}, "vi", "normalize")

    assert result["summary"] == "Học sinh yêu thích dữ liệu"


def test_cv_lockout_limiter_locks_for_ten_minutes_after_sixth_request(monkeypatch):
    now = 1000.0
    monkeypatch.setattr(rate_limit, "monotonic", lambda: now)
    limiter = LockoutRateLimiter(limit=5, window_seconds=600, lockout_seconds=600)

    for _ in range(5):
        limiter.check("user:ip")

    with pytest.raises(HTTPException) as error:
        limiter.check("user:ip")

    assert error.value.status_code == 429
    assert error.value.headers["Retry-After"] == "600"

    now += 300
    with pytest.raises(HTTPException) as error:
        limiter.check("user:ip")
    assert error.value.headers["Retry-After"] == "300"

    now += 300
    assert limiter.check("user:ip") == 4


def test_sliding_window_limit_is_atomic_for_concurrent_requests():
    limiter = SlidingWindowRateLimiter(limit=5, window_seconds=60)
    barrier = Barrier(20)

    def request():
        barrier.wait()
        try:
            limiter.check("same-user:same-ip")
            return True
        except HTTPException as error:
            assert error.status_code == 429
            return False

    with ThreadPoolExecutor(max_workers=20) as executor:
        admitted = list(executor.map(lambda _: request(), range(20)))

    assert sum(admitted) == 5


def test_authentication_failure_limiter_blocks_repeated_failures_and_resets(monkeypatch):
    now = 1000.0
    monkeypatch.setattr(rate_limit, "monotonic", lambda: now)
    limiter = AuthenticationFailureRateLimiter(limit=2, window_seconds=60, lockout_seconds=120)

    limiter.check("opaque-email-key")
    limiter.record_failure("opaque-email-key")
    limiter.check("opaque-email-key")
    limiter.record_failure("opaque-email-key")
    with pytest.raises(HTTPException) as error:
        limiter.check("opaque-email-key")
    assert error.value.status_code == 429
    assert error.value.headers["Retry-After"] == "120"

    limiter.reset("opaque-email-key")
    assert limiter.check("opaque-email-key") is None


def test_cv_normalization_prompt_preserves_language_and_forbids_invented_facts():
    service = AIService(Settings(groq_api_key="", groq_model="test-model"))
    service._client = Mock()
    service._client.chat.completions.create.return_value.choices = [
        SimpleNamespace(message=SimpleNamespace(content='{"summary":"Nội dung đã sửa"}'))
    ]

    service.generate_cv({"summary": "Nội dung"}, "vi", "normalize")

    system_prompt = service._client.chat.completions.create.call_args.kwargs["messages"][0]["content"]
    assert "Improve spelling, grammar" in system_prompt
    assert "input language" in system_prompt
    assert "Do not add claims or invent experience" in system_prompt
    assert "Translate every human-written value" not in system_prompt


def test_cv_ai_response_must_preserve_input_shape():
    service = AIService(Settings(groq_api_key="test-key", groq_model="test-model"))
    service._client = Mock()
    service._client.chat.completions.create.return_value.choices = [
        SimpleNamespace(message=SimpleNamespace(content='{"summary":"Edited","extra":"unexpected"}'))
    ]

    with pytest.raises(ValueError, match="invalid CV structure"):
        service.generate_cv({"summary": "Original"}, "en", "normalize")
