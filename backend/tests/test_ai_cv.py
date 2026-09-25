import pytest
from pydantic import ValidationError

from app.api.routes.ai import CVRequest
from app.core.config import Settings
from app.services.ai import AIService


def test_cv_request_accepts_translation_payload():
    request = CVRequest(data={"summary": "Học sinh yêu thích dữ liệu"}, language="en")

    assert request.operation == "translate"
    assert request.data["summary"]


def test_cv_request_rejects_unsupported_language():
    with pytest.raises(ValidationError):
        CVRequest(data={"summary": "text"}, language="fr")


def test_cv_fallback_without_provider_key_translates_content():
    service = AIService(Settings(groq_api_key="", groq_model="test-model"))
    result = service.generate_cv({"summary": "Học sinh yêu thích dữ liệu"}, "en", "translate")

    assert result["summary"] == "student yêu thích dữ liệu"


def test_cv_fallback_without_provider_key_normalizes_content():
    service = AIService(Settings(groq_api_key="", groq_model="test-model"))
    result = service.generate_cv({"summary": "  Học sinh   yêu thích  dữ liệu  "}, "vi", "normalize")

    assert result["summary"] == "Học sinh yêu thích dữ liệu"
