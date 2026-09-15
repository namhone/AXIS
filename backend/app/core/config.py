from functools import lru_cache
import json
from secrets import token_urlsafe
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "FuturePath API"
    environment: str = "development"
    database_url: str = "sqlite:///./dev.db"
    jwt_secret_key: str = "FUTUREPATH_LOCAL_SECRET_KEY_PROTOTYPE"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    cookie_name: str = "futurepath_access_token"
    cookie_secure: bool = False
    cors_origins: Annotated[list[str], NoDecode] = [
        "https://axis-career-app.vercel.app",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ]
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
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
    def validate_cors_origins(cls, value: list[str]) -> list[str]:
        if "*" in value:
            raise ValueError("CORS_ORIGINS must contain explicit origins, not '*'")
        if not value:
            return [
                "https://axis-career-app.vercel.app",
                "http://localhost:3000",
                "http://localhost:4173",
                "http://127.0.0.1:4173",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
                "http://localhost:5500",
                "http://127.0.0.1:5500",
            ]
        return value

    def signing_key(self) -> str:
        """Return a key without committing a secret to source control.

        A process-local key keeps local imports and development runs usable when
        ``JWT_SECRET_KEY`` is omitted. Deployments must set a stable secret so
        tokens survive restarts.
        """

        if not self.jwt_secret_key:
            self.jwt_secret_key = token_urlsafe(32)
        return self.jwt_secret_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
