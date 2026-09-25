import uuid

from app.api.routes.learning import create_goal
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


def test_post_goal_appends_without_replacing_existing_goals():
    db = AppendSession()
    user = User(id=uuid.uuid4(), email="append@example.com", password_hash="unused", is_active=True)

    first = create_goal(GoalPayload(title="Mục tiêu thứ nhất"), user, db)
    second = create_goal(GoalPayload(title="Mục tiêu thứ hai"), user, db)

    assert first["title"] == "Mục tiêu thứ nhất"
    assert second["title"] == "Mục tiêu thứ hai"
    assert [goal.title for goal in db.goals] == ["Mục tiêu thứ nhất", "Mục tiêu thứ hai"]
