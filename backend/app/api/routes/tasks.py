from datetime import date, datetime, time, timedelta, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..deps import get_current_user
from ...core.database import get_db
from ...models.tasks import CustomTag, Task
from ...models.user import User
from ...schemas.tasks import (
    CalendarResponse,
    GeneratePlanPayload,
    TagPayload,
    TaskPayload,
    TaskStatusPayload,
)
from ...services.task_planner import (
    ACTIVE_STATUSES,
    DAILY_MINUTE_LIMIT,
    DAILY_TASK_LIMIT,
    reconcile_overdue_tasks,
)

router = APIRouter(prefix="/api/v1", tags=["tasks"])
AI_TAG_COLOR = "#8B5CF6"
AI_TAG_ID = uuid.UUID(int=0)


def _tag_dict(tag: CustomTag, user_id: uuid.UUID) -> dict:
    return {"tag_id": tag.id, "user_id": user_id, "tag_name": tag.tag_name, "color_hex": tag.color_hex}


def _task_dict(task: Task) -> dict:
    tags = [_tag_dict(tag, task.user_id) for tag in task.tags]
    if task.is_ai_generated:
        tags.insert(0, {"tag_id": AI_TAG_ID, "user_id": task.user_id, "tag_name": "AI Task", "color_hex": AI_TAG_COLOR})
    return {
        "task_id": task.id,
        "user_id": task.user_id,
        "task_name": task.task_name,
        "description": task.description,
        "estimated_time_minutes": task.estimated_time_minutes,
        "scheduled_date": task.scheduled_date,
        "status": task.status,
        "is_ai_generated": task.is_ai_generated,
        "generated_at": task.generated_at,
        "tags": tags,
    }


def _ensure_tag_ownership(db: Session, tag_ids: list[uuid.UUID], user_id: uuid.UUID) -> list[CustomTag]:
    if not tag_ids:
        return []
    tags = db.query(CustomTag).filter(CustomTag.user_id == user_id, CustomTag.id.in_(tag_ids)).all()
    if len(tags) != len(set(tag_ids)):
        raise HTTPException(status_code=404, detail="One or more tags do not belong to this account")
    return tags


def _ensure_capacity(db: Session, user_id: uuid.UUID, scheduled_date: date, minutes: int, task_id: uuid.UUID | None = None) -> None:
    query = db.query(Task).filter(
        Task.user_id == user_id,
        Task.scheduled_date == scheduled_date,
        Task.status.in_(ACTIVE_STATUSES),
    )
    if task_id:
        query = query.filter(Task.id != task_id)
    active = query.all()
    if len(active) >= DAILY_TASK_LIMIT or sum(item.estimated_time_minutes for item in active) + minutes > DAILY_MINUTE_LIMIT:
        raise HTTPException(status_code=409, detail="This day is full: maximum 4 tasks and 180 minutes")


def _reconcile(db: Session, user_id: uuid.UUID) -> list[uuid.UUID]:
    moved = reconcile_overdue_tasks(db, user_id)
    if moved:
        db.commit()
    return moved


@router.get("/tasks", response_model=None)
def list_tasks(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    moved = _reconcile(db, user.id)
    query = db.query(Task).filter(Task.user_id == user.id)
    if from_date:
        query = query.filter(Task.scheduled_date >= from_date)
    if to_date:
        query = query.filter(Task.scheduled_date <= to_date)
    tasks = query.order_by(Task.scheduled_date, Task.created_at).all()
    return {
        "user_id": user.id,
        "generated_at": datetime.now(timezone.utc),
        "plan_duration_days": 3,
        "tasks": [_task_dict(task) for task in tasks],
        "calendar_metadata": {"auto_rescheduled_count": len(moved), "shifted_tasks_from_past": moved},
    }


@router.post("/tasks/generate", response_model=CalendarResponse)
def generate_plan(
    payload: GeneratePlanPayload | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _reconcile(db, user.id)
    latest_batch = (
        db.query(Task)
        .filter(Task.user_id == user.id, Task.is_ai_generated.is_(True), Task.batch_id.is_not(None))
        .order_by(Task.generated_at.desc())
        .first()
    )
    if latest_batch and latest_batch.batch_id:
        batch_tasks = db.query(Task).filter(Task.user_id == user.id, Task.batch_id == latest_batch.batch_id).all()
        if batch_tasks and any(task.status != "COMPLETED" for task in batch_tasks):
            raise HTTPException(status_code=409, detail="Complete the current 3-day AI plan before generating another")

    now = datetime.now(timezone.utc)
    batch_id = uuid.uuid4()
    names = (payload.task_names if payload else []) or [
        "Ôn tập kiến thức trọng tâm",
        "Luyện tập kỹ năng theo mục tiêu",
        "Đọc và ghi chú tài liệu chuyên ngành",
        "Hoàn thiện một sản phẩm nhỏ",
        "Tự đánh giá tiến độ",
        "Lập bước tiếp theo",
    ]
    created: list[Task] = []
    for index, name in enumerate(names[:12]):
        day = date.today() + timedelta(days=index // 2)
        task = Task(
            user_id=user.id,
            task_name=name.strip() or f"Nhiệm vụ ngày {index // 2 + 1}",
            description="Thực hiện nội dung theo mục tiêu cá nhân trong ngày. Hoàn thành và ghi lại kết quả đạt được.",
            estimated_time_minutes=45,
            scheduled_date=day,
            status="PENDING",
            is_ai_generated=True,
            batch_id=batch_id,
            generated_at=now,
        )
        created.append(task)
    db.add_all(created)
    db.commit()
    for task in created:
        db.refresh(task)
    return {
        "user_id": user.id,
        "generated_at": now,
        "plan_duration_days": 3,
        "tasks": [_task_dict(task) for task in created],
        "calendar_metadata": {"auto_rescheduled_count": 0, "shifted_tasks_from_past": []},
    }


@router.post("/tasks", status_code=status.HTTP_201_CREATED, response_model=None)
def create_task(payload: TaskPayload, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    _reconcile(db, user.id)
    _ensure_capacity(db, user.id, payload.scheduled_date, payload.estimated_time_minutes)
    task = Task(user_id=user.id, **payload.model_dump(exclude={"tag_ids"}))
    task.tags = _ensure_tag_ownership(db, payload.tag_ids, user.id)
    db.add(task)
    db.commit()
    db.refresh(task)
    return _task_dict(task)


@router.patch("/tasks/{task_id}/status", response_model=None)
def update_task_status(
    task_id: uuid.UUID,
    payload: TaskStatusPayload,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = payload.status
    db.commit()
    db.refresh(task)
    return _task_dict(task)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()


@router.get("/tags", response_model=None)
def list_tags(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    return [_tag_dict(tag, user.id) for tag in db.query(CustomTag).filter(CustomTag.user_id == user.id).order_by(CustomTag.tag_name).all()]


@router.post("/tags", status_code=status.HTTP_201_CREATED, response_model=None)
def create_tag(payload: TagPayload, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    tag = CustomTag(user_id=user.id, **payload.model_dump())
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return _tag_dict(tag, user.id)


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(tag_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    tag = db.query(CustomTag).filter(CustomTag.id == tag_id, CustomTag.user_id == user.id).first()
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    db.delete(tag)
    db.commit()
