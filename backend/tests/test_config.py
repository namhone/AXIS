import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_development_allows_ephemeral_signing_key() -> None:
    settings = Settings(environment="development", jwt_secret_key="")

    first_key = settings.signing_key()
    assert len(first_key) >= 32
    assert settings.signing_key() == first_key


def test_production_requires_strong_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(
            environment="production",
            jwt_secret_key="too-short",
            cookie_secure=True,
        )


def test_production_requires_secure_cookies() -> None:
    with pytest.raises(ValidationError, match="COOKIE_SECURE"):
        Settings(
            environment="production",
            jwt_secret_key="x" * 64,
            cookie_secure=False,
        )


def test_production_accepts_strong_secret_and_secure_cookies() -> None:
    settings = Settings(
        environment="production",
        jwt_secret_key="x" * 64,
        cookie_secure=True,
    )

    assert settings.signing_key() == "x" * 64


def test_development_allows_loopback_live_server_origins() -> None:
    settings = Settings(
        _env_file=None,
        environment="development",
        cors_origins=None,
    )

    assert "http://localhost:5501" in settings.cors_origins
    assert "http://127.0.0.1:5501" in settings.cors_origins


def test_production_defaults_to_same_origin_without_localhost_origins() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        jwt_secret_key="x" * 64,
        cookie_secure=True,
        cors_origins=None,
    )

    assert settings.cors_origins == ["https://axis-career-app.vercel.app"]


def test_development_adds_live_server_origins_to_custom_allowlist() -> None:
    settings = Settings(
        _env_file=None,
        environment="development",
        cors_origins=["https://preview.example"],
    )

    assert settings.cors_origins == [
        "https://preview.example",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5501",
        "http://127.0.0.1:5501",
    ]


def test_production_preserves_explicit_cors_allowlist_without_dev_origins() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        jwt_secret_key="x" * 64,
        cookie_secure=True,
        cors_origins=["https://preview.example"],
    )

    assert settings.cors_origins == ["https://preview.example"]


def test_vercel_production_system_environment_enables_strict_defaults(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("VERCEL_URL", "axis-career-app.vercel.app")
    for key in ("ENVIRONMENT", "COOKIE_SECURE", "CORS_ORIGINS"):
        monkeypatch.delenv(key, raising=False)

    settings = Settings(_env_file=None, jwt_secret_key="x" * 64)

    assert settings.environment == "production"
    assert settings.cookie_secure is True
    assert settings.cors_origins == ["https://axis-career-app.vercel.app"]


def test_vercel_preview_uses_deployment_origin_and_secure_cookie(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setenv("VERCEL_URL", "axis-preview-123.vercel.app")
    for key in ("ENVIRONMENT", "COOKIE_SECURE", "CORS_ORIGINS"):
        monkeypatch.delenv(key, raising=False)

    settings = Settings(_env_file=None, jwt_secret_key="x" * 64)

    assert settings.environment == "preview"
    assert settings.cookie_secure is True
    assert settings.cors_origins == ["https://axis-preview-123.vercel.app"]


def test_vercel_preview_rejects_weak_secret(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setenv("VERCEL_URL", "axis-preview-123.vercel.app")
    for key in ("ENVIRONMENT", "COOKIE_SECURE", "CORS_ORIGINS"):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(_env_file=None, jwt_secret_key="short")
