from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ...core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
@router.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
@router.get("/api/v1/health/ready")
def readiness(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ready"}
