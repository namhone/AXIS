import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.routes.learning import create_goal
from app.api.routes.learning import update_goal
from app.core.database import Base
from app.models.learning import Goal
from app.schemas.learning import GoalPayload
from app.models.user import User


class AppendSession:
    def __init__(self):
        self.goals = []

    def add(self, goal):
        self.goals.append(goal)

    def commit(self):
        return None

    def refresh(self, goal):
        if goal.id is None:
            goal.id = uuid.uuid4()


def _goal_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_post_goal_appends_without_replacing_existing_goals():
    db = AppendSession()
    user = User(id=uuid.uuid4(), email="append@example.com", password_hash="unused", is_active=True)

    first = create_goal(GoalPayload(title="Mục tiêu thứ nhất"), user, db)
    second = create_goal(GoalPayload(title="Mục tiêu thứ hai"), user, db)

    assert first["title"] == "Mục tiêu thứ nhất"
    assert second["title"] == "Mục tiêu thứ hai"
    assert [goal.title for goal in db.goals] == ["Mục tiêu thứ nhất", "Mục tiêu thứ hai"]


def test_cancelled_career_goals_do_not_count_toward_creation_limit():
    db = _goal_session()
    user = User(id=uuid.uuid4(), email="cancelled-create", password_hash="unused", is_active=True)
    db.add(user)
    db.add_all(
        [
            Goal(
                user_id=user.id,
                title=f"Cancelled career {code}",
                category="career",
                status="cancelled",
                note=f"__axis_career_code:{code}__",
            )
            for code in ("N01", "N02")
        ]
    )
    db.commit()

    created = create_goal(
        GoalPayload(title="Replacement career", category="career", career_code="N03"),
        user,
        db,
    )

    assert created["career_code"] == "N03"
    assert db.query(Goal).filter(Goal.user_id == user.id, Goal.category == "career").count() == 3
    db.close()


def test_cancelled_career_goals_do_not_count_toward_update_limit():
    db = _goal_session()
    user = User(id=uuid.uuid4(), email="cancelled-update", password_hash="unused", is_active=True)
    general_goal = Goal(user_id=user.id, title="General goal", category="general", status="pending")
    db.add_all(
        [
            user,
            general_goal,
            *[
                Goal(
                    user_id=user.id,
                    title=f"Cancelled career {code}",
                    category="career",
                    status="cancelled",
                    note=f"__axis_career_code:{code}__",
                )
                for code in ("N01", "N02")
            ],
        ]
    )
    db.commit()

    updated = update_goal(
        general_goal.id,
        GoalPayload(title="Replacement career", category="career", career_code="N03"),
        user,
        db,
    )

    assert updated["career_code"] == "N03"
    assert updated["category"] == "career"
    db.close()


def test_reactivating_cancelled_career_goal_cannot_exceed_active_limit():
    db = _goal_session()
    user = User(id=uuid.uuid4(), email="reactivate-limit", password_hash="unused", is_active=True)
    cancelled = Goal(
        user_id=user.id,
        title="Cancelled career N01",
        category="career",
        status="cancelled",
        note="__axis_career_code:N01__",
    )
    active_goals = [
        Goal(
            user_id=user.id,
            title=f"Active career {code}",
            category="career",
            status="pending",
            note=f"__axis_career_code:{code}__",
        )
        for code in ("N02", "N03")
    ]
    db.add_all([user, cancelled, *active_goals])
    db.commit()

    with pytest.raises(HTTPException) as error:
        update_goal(
            cancelled.id,
            GoalPayload(
                title=cancelled.title,
                category="career",
                career_code="N01",
                status="pending",
            ),
            user,
            db,
        )

    assert error.value.status_code == 409
    db.refresh(cancelled)
    assert cancelled.status == "cancelled"
    db.close()
