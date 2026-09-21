import json
from datetime import date, timedelta
import uuid
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import Base
from app.models.tasks import Task
from app.schemas.tasks import TaskPayload
from app.services.ai import AIService
from app.services.schedule import _expand_tasks
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


def test_expand_tasks_keeps_subtasks_as_independent_titles():
    expanded = _expand_tasks(
        {
            "title": "Ôn tập Hình học",
            "subtasks": ["Làm bài 1-3", "Làm bài 4-5"],
        },
        "Ôn tập",
    )

    assert [task["title"] for task in expanded] == ["Làm bài 1-3", "Làm bài 4-5"]
    assert all(task["task_id"] for task in expanded)


def test_ai_service_accepts_vietjack_reference_tasks(monkeypatch):
    class DummyCompletions:
        @staticmethod
        def create(**kwargs):
            payload = {
                "steps": [
                    {
                        "step_number": 1,
                        "title": "Ngày 1",
                        "tasks": [
                            {
                                "title": "Làm bài mục 1 của Bài 1 Hệ thức lượng trong tam giác vuông",
                                "minutes": 45,
                                "status": "pending",
                                "resources": [{"title": "VietJack", "url": "https://vietjack.com"}],
                            }
                        ],
                    },
                    {"step_number": 2, "title": "Ngày 2", "tasks": []},
                    {"step_number": 3, "title": "Ngày 3", "tasks": []},
                    {"step_number": 4, "title": "Ngày 4", "tasks": []},
                    {"step_number": 5, "title": "Ngày 5", "tasks": []},
                    {"step_number": 6, "title": "Ngày 6", "tasks": []},
                    {"step_number": 7, "title": "Ngày 7", "tasks": []},
                ]
            }
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload, ensure_ascii=False)))]
            )

    monkeypatch.setattr(
        "app.services.ai.OpenAI",
        lambda *args, **kwargs: SimpleNamespace(chat=SimpleNamespace(completions=DummyCompletions())),
    )

    service = AIService(Settings(groq_api_key="test-key", groq_model="test-model"))
    roadmap = service.generate_roadmap({"goal": "Học tốt"}, [{"title": "Toán học"}])

    assert len(roadmap) == 7
    assert roadmap[0]["tasks"][0]["resources"][0]["title"] == "VietJack"
