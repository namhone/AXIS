from datetime import date, timedelta
import uuid

from sqlalchemy.orm import Session

from ..models.tasks import Task

DAILY_TASK_LIMIT = 4
DAILY_MINUTE_LIMIT = 180
ACTIVE_STATUSES = ("PENDING", "IN_PROGRESS")


def _day_load(db: Session, user_id: uuid.UUID, day: date) -> tuple[int, int]:
    rows = (
        db.query(Task)
        .filter(Task.user_id == user_id, Task.scheduled_date == day, Task.status.in_(ACTIVE_STATUSES))
        .all()
    )
    return len(rows), sum(row.estimated_time_minutes for row in rows)


def _next_available_day(db: Session, user_id: uuid.UUID, start: date, minutes: int) -> date:
    target = start
    while True:
        count, total = _day_load(db, user_id, target)
        if count < DAILY_TASK_LIMIT and total + minutes <= DAILY_MINUTE_LIMIT:
            return target
        target += timedelta(days=1)


def reconcile_overdue_tasks(db: Session, user_id: uuid.UUID, today: date | None = None) -> list[uuid.UUID]:
    """Move active overdue work to today, then push conflicts to later capacity."""
    today = today or date.today()
    overdue = (
        db.query(Task)
        .filter(
            Task.user_id == user_id,
            Task.scheduled_date < today,
            Task.status.in_(ACTIVE_STATUSES),
        )
        .order_by(Task.scheduled_date, Task.created_at)
        .all()
    )
    moved: list[uuid.UUID] = []
    for task in overdue:
        task.auto_rescheduled_from = task.scheduled_date
        task.scheduled_date = today
        moved.append(task.id)

    # Preserve overdue work on today where possible; shift ordinary work first.
    for day_offset in range(0, 366):
        day = today + timedelta(days=day_offset)
        active = (
            db.query(Task)
            .filter(Task.user_id == user_id, Task.scheduled_date == day, Task.status.in_(ACTIVE_STATUSES))
            .order_by(Task.auto_rescheduled_from.is_(None).desc(), Task.created_at.desc())
            .all()
        )
        while len(active) > DAILY_TASK_LIMIT or sum(item.estimated_time_minutes for item in active) > DAILY_MINUTE_LIMIT:
            candidate = next((item for item in reversed(active) if item.auto_rescheduled_from is None), active[-1])
            target = _next_available_day(db, user_id, day + timedelta(days=1), candidate.estimated_time_minutes)
            candidate.scheduled_date = target
            active.remove(candidate)
    return moved


def validate_batch_capacity(tasks: list[Task]) -> None:
    grouped: dict[date, list[Task]] = {}
    for task in tasks:
        grouped.setdefault(task.scheduled_date, []).append(task)
    if any(len(day_tasks) > DAILY_TASK_LIMIT for day_tasks in grouped.values()):
        raise ValueError("A day cannot contain more than 4 active tasks")
    if any(sum(task.estimated_time_minutes for task in day_tasks) > DAILY_MINUTE_LIMIT for day_tasks in grouped.values()):
        raise ValueError("A day cannot contain more than 180 active minutes")
