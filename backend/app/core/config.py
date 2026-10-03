from functools import lru_cache
import json
from secrets import token_urlsafe
from typing import Annotated

from pydantic import field_validator, model_validator
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


class Settings(BaseSettings):
    """Application settings loaded from environment variables or ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Axis API"
    environment: str = "development"
    database_url: str = "sqlite:///./dev.db"
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    cookie_name: str = "axis_access_token"
    cookie_secure: bool = False
    cors_origins: Annotated[list[str] | None, NoDecode] = None
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    ai_rate_limit_requests: int = 5
    ai_rate_limit_window_seconds: int = 60

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
        is_production = environment in {"production", "prod"}
        if not self.cors_origins:
            self.cors_origins = list(
                PRODUCTION_CORS_ORIGINS if is_production else DEVELOPMENT_CORS_ORIGINS
            )
        elif not is_production:
            self.cors_origins.extend(
                origin
                for origin in LOCAL_DEVELOPMENT_ORIGINS
                if origin not in self.cors_origins
            )
        if is_production:
            if len(self.jwt_secret_key.strip()) < 32:
                raise ValueError(
                    "JWT_SECRET_KEY must be at least 32 characters in production"
                )
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in production")
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
