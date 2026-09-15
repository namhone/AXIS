from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


def _engine_options(database_url: str) -> dict[str, object]:
    if database_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}


def _resolve_database_url(database_url: str) -> str:
    """Use the bundled local database when a relative SQLite URL is used."""

    database_url = database_url.strip().strip('"').strip("'")
    if database_url.startswith("postgres://"):
        return "postgresql+psycopg2://" + database_url[len("postgres://"):]
    if database_url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + database_url[len("postgresql://"):]
    if database_url != "sqlite:///./dev.db":
        return database_url
    local_database = Path.cwd() / "dev.db"
    bundled_database = Path(__file__).resolve().parents[2] / "dev.db"
    database_path = local_database if local_database.exists() else bundled_database
    return "sqlite:///" + database_path.resolve().as_posix()


settings = get_settings()
database_url = _resolve_database_url(settings.database_url)
engine = create_engine(
    database_url,
    future=True,
    **_engine_options(database_url),
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """Yield a request-scoped synchronous SQLAlchemy session."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
