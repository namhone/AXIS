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
