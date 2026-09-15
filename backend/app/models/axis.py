import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class CompetencyScore(Base):
    __tablename__ = "competency_scores"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    s1: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    s2: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    s3: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    s4: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    s5: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    normalized_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class CareerBenchmark(Base):
    __tablename__ = "career_benchmarks"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    requirements_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    ahp_matrix_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    roc_order_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class MatchLog(Base):
    __tablename__ = "match_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    competency_score_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("competency_scores.id", ondelete="SET NULL"), nullable=True)
    results_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
