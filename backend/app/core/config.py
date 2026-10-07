from functools import lru_cache
import json
import os
from secrets import token_urlsafe
from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


PRODUCTION_CORS_ORIGINS = ("https://axis-career-app.vercel.app",)
DEVELOPMENT_CORS_ORIGINS = (
    "https://axis-career-app.vercel.app",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:5501",
    "http://127.0.0.1:5501",
)
LOCAL_DEVELOPMENT_ORIGINS = (
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:5501",
    "http://127.0.0.1:5501",
)


def _vercel_environment() -> str:
    """Use Vercel's runtime environment when the app-specific setting is absent."""

    if os.getenv("VERCEL", "").strip() == "1":
        value = os.getenv("VERCEL_ENV", "").strip().lower()
        if value in {"production", "preview", "development"}:
            return value
    return "development"


def _vercel_cookie_secure() -> bool:
    return os.getenv("VERCEL", "").strip() == "1" and os.getenv(
        "VERCEL_ENV", ""
    ).strip().lower() in {"production", "preview"}


class Settings(BaseSettings):
    """Application settings loaded from environment variables or ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Axis API"
    environment: str = Field(default_factory=_vercel_environment)
    database_url: str = "sqlite:///./dev.db"
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    cookie_name: str = "axis_access_token"
    cookie_secure: bool = Field(default_factory=_vercel_cookie_secure)
    cors_origins: Annotated[list[str] | None, NoDecode] = None
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    ai_rate_limit_requests: int = 5
    ai_rate_limit_window_seconds: int = 60
    auth_login_failure_limit: int = 5
    auth_login_window_seconds: int = 900
    auth_login_lockout_seconds: int = 900

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            raw = value.strip()
            if not raw or raw.lower() in {"null", "none", "undefined"}:
                return []
            if raw.lstrip().startswith("["):
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [origin.strip() for origin in parsed if isinstance(origin, str) and origin.strip() and origin.strip().lower() not in {"null", "none", "undefined"}]
                return []
            return [
                origin.strip()
                for origin in raw.split(",")
                if origin.strip() and origin.strip().lower() not in {"null", "none", "undefined"}
            ]
        if isinstance(value, list):
            return [origin.strip() for origin in value if isinstance(origin, str) and origin.strip() and origin.strip().lower() not in {"null", "none", "undefined"}]
        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: list[str] | None) -> list[str] | None:
        if value is not None and "*" in value:
            raise ValueError("CORS_ORIGINS must contain explicit origins, not '*'")
        return value

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        environment = self.environment.strip().lower()
        vercel = os.getenv("VERCEL", "").strip() == "1"
        vercel_environment = os.getenv("VERCEL_ENV", "").strip().lower()
        is_vercel_deployment = vercel and vercel_environment in {"production", "preview"}
        is_production = environment in {"production", "prod"} or (
            vercel and vercel_environment == "production"
        )
        if vercel and vercel_environment == "production":
            self.environment = "production"
        elif is_vercel_deployment:
            self.environment = "preview"
        if not self.cors_origins:
            vercel_url = os.getenv("VERCEL_URL", "").strip().rstrip("/")
            if is_vercel_deployment and vercel_url:
                self.cors_origins = [f"https://{vercel_url}"]
            elif is_vercel_deployment:
                raise ValueError("VERCEL_URL is required for Vercel deployment CORS defaults")
            else:
                self.cors_origins = list(
                    PRODUCTION_CORS_ORIGINS if is_production else DEVELOPMENT_CORS_ORIGINS
                )
        elif not is_production:
            if not is_vercel_deployment:
                self.cors_origins.extend(
                    origin
                    for origin in LOCAL_DEVELOPMENT_ORIGINS
                    if origin not in self.cors_origins
                )
        if is_production or is_vercel_deployment:
            if len(self.jwt_secret_key.strip()) < 32:
                raise ValueError(
                    "JWT_SECRET_KEY must be at least 32 characters in deployed environments"
                )
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in deployed environments")
        return self

    def signing_key(self) -> str:
        """Return a configured key, or generate an ephemeral development key.

        Development can run without a configured secret, but production is
        rejected by validation before this method can be called.
        """

        if not self.jwt_secret_key:
            self.jwt_secret_key = token_urlsafe(32)
        return self.jwt_secret_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
