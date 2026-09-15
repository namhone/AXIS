import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import get_current_user
from ...core.database import get_db
from ...models.learning import Assessment, Goal, RoadmapStep
from ...models.user import User
from ...schemas.learning import AssessmentPayload, GoalPayload, RoadmapStepPayload, RoadmapTaskDeferPayload
from ...services.schedule import (
    DAILY_TASK_LIMIT,
    MAX_DEFERRALS,
    parse_step_content,
    reconcile_overdue_steps,
)
import json
from ...services.career_matching import calculate_matches
from ...services.skill_planner import build_skill_plan
from ...models.profile import Profile

router = APIRouter(prefix="/api/v1", tags=["learning-data"])


def _goal_dict(goal: Goal) -> dict:
    return {
        "id": str(goal.id),
        "title": goal.title,
        "target_date": goal.target_date,
        "status": goal.status,
        "minutes_per_day": goal.minutes_per_day,
        "note": goal.note,
        "category": goal.category,
    }


def _step_dict(step: RoadmapStep) -> dict:
    return {
        "id": str(step.id),
        "step_number": step.step_number,
        "title": step.title,
        "content": step.content,
        "is_completed": step.is_completed,
    }


@router.get("/skill-plan", response_model=None)
def get_skill_plan(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    profile = db.get(Profile, user.id)
    profile_data = dict(profile.data) if profile else {}
    latest_assessment = (
        db.query(Assessment)
        .filter(Assessment.user_id == user.id)
        .order_by(Assessment.created_at.desc())
        .first()
    )
    if latest_assessment:
        profile_data["career_matches"] = latest_assessment.career_suggestions_json.get("top3", [])
    return build_skill_plan(profile_data)


@router.put("/skill-plan/order", response_model=None)
def save_skill_order(
    payload: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    order = payload.get("skill_order")
    if not isinstance(order, list) or not all(isinstance(item, str) and item.strip() for item in order):
        raise HTTPException(status_code=422, detail="skill_order must be a non-empty array of strings")
    profile = db.get(Profile, user.id)
    if profile is None:
        profile = Profile(user_id=user.id, data={"skillOrder": order})
        db.add(profile)
    else:
        data = dict(profile.data)
        data["skillOrder"] = order
        profile.data = data
    db.commit()
    return get_skill_plan(user, db)


@router.get("/goals", response_model=None)
def list_goals(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Goal]:
    return [_goal_dict(goal) for goal in db.query(Goal).filter(Goal.user_id == user.id).order_by(Goal.target_date, Goal.title).all()]


@router.post("/goals", status_code=status.HTTP_201_CREATED, response_model=None)
def create_goal(payload: GoalPayload, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Goal:
    goal = Goal(user_id=user.id, **payload.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return _goal_dict(goal)


@router.put("/goals/{goal_id}", response_model=None)
def update_goal(goal_id: uuid.UUID, payload: GoalPayload, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Goal:
    goal = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user.id).first()
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    for key, value in payload.model_dump().items():
        setattr(goal, key, value)
    db.commit()
    db.refresh(goal)
    return _goal_dict(goal)


@router.put("/goals", response_model=None)
def replace_goals(
    payload: list[GoalPayload],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Goal]:
    db.query(Goal).filter(Goal.user_id == user.id).delete()
    goals = [Goal(user_id=user.id, **item.model_dump()) for item in payload]
    db.add_all(goals)
    db.commit()
    return [_goal_dict(goal) for goal in goals]


@router.delete("/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(goal_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    goal = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user.id).first()
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    db.delete(goal)
    db.commit()


@router.get("/roadmap", response_model=None)
def list_roadmap(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[RoadmapStep]:
    steps = db.query(RoadmapStep).filter(RoadmapStep.user_id == user.id).order_by(RoadmapStep.step_number).all()
    if reconcile_overdue_steps(steps):
        db.commit()
    return [_step_dict(step) for step in steps]


@router.get("/roadmap/today", response_model=None)
def get_today_roadmap(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    steps = db.query(RoadmapStep).filter(RoadmapStep.user_id == user.id).order_by(RoadmapStep.step_number).all()
    if reconcile_overdue_steps(steps):
        db.commit()
    today = date.today().isoformat()
    for step in steps:
        schedule = parse_step_content(step.content)
        if schedule.get("date") == today:
            return {"date": today, "step": _step_dict(step), "tasks": schedule.get("tasks", [])}
    return {"date": today, "step": None, "tasks": []}


@router.put("/roadmap", response_model=None)
def replace_roadmap(payload: list[RoadmapStepPayload], user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[RoadmapStep]:
    db.query(RoadmapStep).filter(RoadmapStep.user_id == user.id).delete()
    steps = [RoadmapStep(user_id=user.id, **item.model_dump()) for item in payload]
    db.add_all(steps)
    db.commit()
    return [_step_dict(step) for step in steps]


@router.post("/roadmap/tasks/defer", response_model=None)
def defer_roadmap_task(
    payload: RoadmapTaskDeferPayload,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RoadmapStep]:
    steps = db.query(RoadmapStep).filter(RoadmapStep.user_id == user.id).order_by(RoadmapStep.step_number).all()
    source_index = payload.day_number - 1
    if source_index >= len(steps):
        raise HTTPException(status_code=404, detail="Roadmap day not found")
    source = parse_step_content(steps[source_index].content)
    tasks = source.get("tasks", [])
    if payload.task_index >= len(tasks):
        raise HTTPException(status_code=404, detail="Roadmap task not found")
    task = tasks.pop(payload.task_index)
    if not isinstance(task, dict):
        raise HTTPException(status_code=422, detail="Roadmap task is invalid")
    defer_count = int(task.get("defer_count", 0)) + 1
    task["defer_count"] = defer_count
    if defer_count > MAX_DEFERRALS:
        task["completion_percent"] = max(0, int(task.get("completion_percent", 0)) - 10)
        tasks.insert(min(payload.task_index, len(tasks)), task)
    elif source_index < len(steps) - 1:
        target = parse_step_content(steps[source_index + 1].content)
        target_tasks = target.get("tasks", [])
        if len(target_tasks) >= DAILY_TASK_LIMIT:
            removable = next((i for i, item in enumerate(target_tasks) if isinstance(item, dict) and not item.get("user_priority")), None)
            if removable is None:
                removable = len(target_tasks) - 1
            target_tasks.pop(removable)
        target_tasks.insert(0, task)
        target["tasks"] = target_tasks
        steps[source_index + 1].content = json.dumps(target, ensure_ascii=False)
    else:
        tasks.insert(0, task)
    source["tasks"] = tasks
    steps[source_index].content = json.dumps(source, ensure_ascii=False)
    db.commit()
    return [_step_dict(step) for step in steps]


@router.post("/roadmap/tasks/state", response_model=None)
def update_roadmap_task_state(
    payload: RoadmapTaskDeferPayload,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    steps = db.query(RoadmapStep).filter(RoadmapStep.user_id == user.id).order_by(RoadmapStep.step_number).all()
    index = payload.day_number - 1
    if index < 0 or index >= len(steps):
        raise HTTPException(status_code=404, detail="Roadmap day not found")
    schedule = parse_step_content(steps[index].content)
    tasks = schedule.get("tasks", [])
    if payload.task_index < 0 or payload.task_index >= len(tasks):
        raise HTTPException(status_code=404, detail="Roadmap task not found")
    task = tasks[payload.task_index]
    if not isinstance(task, dict):
        raise HTTPException(status_code=422, detail="Roadmap task is invalid")
    task["status"] = "completed"
    task["completion_percent"] = 100
    schedule["tasks"] = tasks
    steps[index].content = json.dumps(schedule, ensure_ascii=False)
    db.commit()
    return {"date": schedule.get("date"), "step": _step_dict(steps[index]), "tasks": tasks}


@router.post("/assessments", status_code=status.HTTP_201_CREATED, response_model=None)
def create_assessment(payload: AssessmentPayload, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Assessment:
    assessment = Assessment(user_id=user.id, **payload.model_dump())
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return {
        "id": str(assessment.id),
        "score_json": assessment.score_json,
        "career_suggestions_json": assessment.career_suggestions_json,
        "created_at": assessment.created_at,
    }


@router.get("/assessments", response_model=None)
def list_assessments(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Assessment]:
    return [
        {
            "id": str(item.id),
            "score_json": item.score_json,
            "career_suggestions_json": item.career_suggestions_json,
            "created_at": item.created_at,
        }
        for item in db.query(Assessment).filter(Assessment.user_id == user.id).order_by(Assessment.created_at.desc()).all()
    ]


@router.post("/assessments/run", response_model=None)
def run_assessment(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    profile = db.get(Profile, user.id)
    profile_data = dict(profile.data) if profile else {}
    profile_data["name"] = user.full_name
    profile_data["email"] = user.email
    result = calculate_matches(profile_data)
    assessment = Assessment(
        user_id=user.id,
        score_json={"riasec": result["riasec"], "top3": result["top3"]},
        career_suggestions_json={"top5": result["top5"], "results": result["results"]},
    )
    db.add(assessment)
    db.commit()
    return result
