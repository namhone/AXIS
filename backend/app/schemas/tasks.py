import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


TaskStatus = Literal["PENDING", "IN_PROGRESS", "COMPLETED"]


class TagPayload(BaseModel):
    tag_name: str = Field(min_length=1, max_length=80)
    color_hex: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class TagResponse(TagPayload):
    tag_id: uuid.UUID
    user_id: uuid.UUID


class TaskPayload(BaseModel):
    task_name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    estimated_time_minutes: int = Field(ge=1, le=180)
    scheduled_date: date
    tag_ids: list[uuid.UUID] = Field(default_factory=list)

    @field_validator("description")
    @classmethod
    def description_has_at_most_three_sentences(cls, value: str) -> str:
        sentences = [part.strip() for part in value.replace("!", ".").replace("?", ".").split(".") if part.strip()]
        if len(sentences) > 3:
            raise ValueError("description must contain at most 3 sentences")
        return value.strip()


class TaskStatusPayload(BaseModel):
    status: TaskStatus


class TaskResponse(BaseModel):
    task_id: uuid.UUID
    user_id: uuid.UUID
    task_name: str
    description: str
    estimated_time_minutes: int
    scheduled_date: date
    status: TaskStatus
    is_ai_generated: bool
    generated_at: datetime | None
    tags: list[TagResponse]


class CalendarMetadata(BaseModel):
    auto_rescheduled_count: int
    shifted_tasks_from_past: list[uuid.UUID]


class CalendarResponse(BaseModel):
    user_id: uuid.UUID
    generated_at: datetime
    plan_duration_days: int
    tasks: list[TaskResponse]
    calendar_metadata: CalendarMetadata


class GeneratePlanPayload(BaseModel):
    task_names: list[str] = Field(default_factory=list, max_length=12)

