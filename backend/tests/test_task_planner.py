from datetime import date, timedelta
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.tasks import Task
from app.schemas.tasks import TaskPayload
from app.services.task_planner import reconcile_overdue_tasks


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_overdue_tasks_move_to_today_and_preserve_daily_limits():
    db = _session()
    user_id = uuid.uuid4()
    yesterday = date.today() - timedelta(days=1)
    for index in range(2):
        db.add(
            Task(
                user_id=user_id,
                task_name=f"Overdue {index}",
                description="Complete the work.",
                estimated_time_minutes=60,
                scheduled_date=yesterday,
                status="PENDING",
            )
        )
    db.add(
        Task(
            user_id=user_id,
            task_name="Today",
            description="Complete the work.",
            estimated_time_minutes=60,
            scheduled_date=date.today(),
            status="PENDING",
        )
    )
    db.commit()

    moved = reconcile_overdue_tasks(db, user_id)
    db.commit()
    tasks = db.query(Task).filter(Task.user_id == user_id).all()

    assert len(moved) == 2
    assert sum(task.scheduled_date == date.today() for task in tasks) == 3
    assert sum(task.estimated_time_minutes for task in tasks if task.scheduled_date == date.today()) <= 180


def test_manual_task_description_rejects_more_than_three_sentences():
    payload = TaskPayload(
        task_name="Task",
        description="One. Two. Three.",
        estimated_time_minutes=30,
        scheduled_date=date.today(),
    )
    assert payload.description == "One. Two. Three."

    try:
        TaskPayload(
            task_name="Task",
            description="One. Two. Three. Four.",
            estimated_time_minutes=30,
            scheduled_date=date.today(),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected sentence limit validation")
