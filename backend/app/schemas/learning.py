from datetime import date
from typing import Any
import uuid

from pydantic import BaseModel, Field


class GoalPayload(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    target_date: date | None = None
    status: str = Field(default="pending", max_length=32)
    minutes_per_day: int | None = Field(default=None, ge=0, le=1440)
    note: str = ""
    category: str = "general"
    career_code: str | None = Field(default=None, max_length=16)


class RoadmapStepPayload(BaseModel):
    step_number: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=255)
    content: str = ""
    is_completed: bool = False


class RoadmapTaskDeferPayload(BaseModel):
    day_number: int = Field(ge=1, le=7)
    task_index: int = Field(ge=0, le=3)


class AssessmentPayload(BaseModel):
    score_json: dict[str, Any] = Field(default_factory=dict)
    career_suggestions_json: dict[str, Any] = Field(default_factory=dict)


class IdResponse(BaseModel):
    id: uuid.UUID
