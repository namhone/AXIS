import json
from datetime import date, timedelta
import uuid
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.database import Base, get_db
from app.api.deps import get_current_user
from app.main import app
from app.models.learning import RoadmapStep
from app.models.tasks import Task
from app.schemas.tasks import TaskPayload
from app.services.ai import AIService
from app.services.schedule import _expand_tasks
from app.services.task_planner import reconcile_overdue_tasks
from app.models.user import User


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
    calls = []

    class DummyCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
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
    profile = {
        "career_matches": [{"code": "N01", "name": "Máy tính & Công nghệ thông tin", "score": 91.5}],
        "career_focus": {
            "recommended": [{"code": "N01", "name": "Máy tính & Công nghệ thông tin", "score": 91.5}],
            "selected": [
                {"code": "N10", "name": "Thiết kế đồ họa", "note": "Tư duy thị giác"},
                {"code": "N12", "name": "Tâm lý học", "note": "Kỹ năng lắng nghe"},
            ],
        },
        "skill_plan": {"tracks": [{"name": "Python nền tảng"}]},
    }
    roadmap = service.generate_roadmap(profile, [{"title": "Toán học"}])

    assert len(roadmap) == 7
    assert roadmap[0]["tasks"][0]["resources"][0]["title"] == "VietJack"
    prompt = calls[0]["messages"]
    input_payload = json.loads(prompt[1]["content"])
    assert input_payload["profile"]["career_focus"]["recommended"][0]["score"] == 91.5
    assert input_payload["profile"]["career_focus"]["selected"][0]["name"] == "Thiết kế đồ họa"
    assert "career_focus.selected" in prompt[0]["content"]
    assert "career_focus.recommended" in prompt[0]["content"]


def _client_with_tasks():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    user = User(
        id=uuid.uuid4(),
        email="task-capacity@example.com",
        full_name="Task Capacity",
        password_hash="unused",
    )
    db.add(user)
    db.commit()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app), db, engine, user


def _close_task_client(db, engine):
    app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_generate_plan_rejects_when_today_has_no_capacity():
    client, db, engine, user = _client_with_tasks()
    try:
        db.add_all([
            Task(
                user_id=user.id,
                task_name=f"Existing {index}",
                description="",
                estimated_time_minutes=30,
                scheduled_date=date.today(),
                status="PENDING",
            )
            for index in range(4)
        ])
        db.commit()

        response = client.post("/api/v1/tasks/generate")

        assert response.status_code == 409
        assert db.query(Task).count() == 4
    finally:
        _close_task_client(db, engine)


def test_reactivating_task_rejects_when_day_is_full():
    client, db, engine, user = _client_with_tasks()
    try:
        completed = Task(
            user_id=user.id,
            task_name="Completed",
            description="",
            estimated_time_minutes=30,
            scheduled_date=date.today(),
            status="COMPLETED",
        )
        db.add(completed)
        db.add_all([
            Task(
                user_id=user.id,
                task_name=f"Active {index}",
                description="",
                estimated_time_minutes=30,
                scheduled_date=date.today(),
                status="PENDING",
            )
            for index in range(4)
        ])
        db.commit()

        response = client.patch(
            f"/api/v1/tasks/{completed.id}/status",
            json={"status": "PENDING"},
        )

        assert response.status_code == 409
        db.refresh(completed)
        assert completed.status == "COMPLETED"
    finally:
        _close_task_client(db, engine)


def test_deferring_task_keeps_target_day_tasks_when_full():
    client, db, engine, user = _client_with_tasks()
    try:
        db.add_all([
            RoadmapStep(
                user_id=user.id,
                step_number=1,
                title="Day 1",
                content=json.dumps({"tasks": [{"title": "Move me", "defer_count": 0}]}),
                is_completed=False,
            ),
            RoadmapStep(
                user_id=user.id,
                step_number=2,
                title="Day 2",
                content=json.dumps({
                    "tasks": [
                        {"title": f"Priority {index}", "user_priority": True}
                        for index in range(4)
                    ]
                }),
                is_completed=False,
            ),
        ])
        db.commit()

        response = client.post(
            "/api/v1/roadmap/tasks/defer",
            json={"day_number": 1, "task_index": 0},
        )

        assert response.status_code == 409
        steps = db.query(RoadmapStep).order_by(RoadmapStep.step_number).all()
        assert json.loads(steps[0].content)["tasks"][0]["title"] == "Move me"
        assert len(json.loads(steps[1].content)["tasks"]) == 4
    finally:
        _close_task_client(db, engine)
