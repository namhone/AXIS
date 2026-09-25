from fastapi import APIRouter, Depends, HTTPException, Request, status
from openai import OpenAIError
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..deps import get_current_user
from ...core.config import get_settings
from ...core.database import get_db
from ...models.learning import Assessment, Goal, RoadmapStep
from ...models.profile import Profile
from ...models.user import User
from ...services.ai import AIService
from ...services.skill_planner import build_skill_plan
from ...services.schedule import normalize_week
from ...core.rate_limit import SlidingWindowRateLimiter

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])
_ai_limiter = SlidingWindowRateLimiter(
    limit=get_settings().ai_rate_limit_requests,
    window_seconds=get_settings().ai_rate_limit_window_seconds,
)


class CVRequest(BaseModel):
    data: dict[str, object] = Field(...)
    language: str = Field(pattern="^(vi|en)$")
    operation: str = Field(default="translate", pattern="^(translate|normalize)$")


class CVResponse(BaseModel):
    data: dict[str, object]
    language: str
    operation: str


def enforce_ai_rate_limit(
    request: Request,
    user: User = Depends(get_current_user),
) -> None:
    _ai_limiter.check(f"{user.id}:{request.client.host if request.client else 'unknown'}")


@router.post("/roadmap", status_code=status.HTTP_200_OK, response_model=None)
def generate_roadmap(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(enforce_ai_rate_limit),
) -> list[RoadmapStep]:
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    goals = db.query(Goal).filter(Goal.user_id == user.id).order_by(Goal.target_date, Goal.title).all()
    latest_assessment = (
        db.query(Assessment)
        .filter(Assessment.user_id == user.id)
        .order_by(Assessment.created_at.desc())
        .first()
    )
    profile_data = dict(profile.data) if profile else {}
    if latest_assessment:
        profile_data["career_matches"] = latest_assessment.career_suggestions_json.get("top3", [])
    profile_data["skill_plan"] = build_skill_plan(profile_data)
    previous_steps = [
        {"content": step.content}
        for step in db.query(RoadmapStep)
        .filter(RoadmapStep.user_id == user.id)
        .order_by(RoadmapStep.step_number)
        .all()
    ]
    try:
        service = AIService(get_settings())
        ai_steps = service.generate_roadmap(
            profile=profile_data,
            goals=[
                {
                    "title": goal.title,
                    "target_date": goal.target_date,
                    "status": goal.status,
                    "minutes_per_day": goal.minutes_per_day,
                    "note": goal.note,
                    "category": goal.category,
                }
                for goal in goals
            ],
        )
        steps = normalize_week(ai_steps, [
            {
                "title": goal.title,
                "target_date": goal.target_date,
                "status": goal.status,
                "note": goal.note,
            }
            for goal in goals
        ], previous_steps=previous_steps)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "ai_unavailable", "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "ai_invalid_response", "message": "AI returned an invalid roadmap"},
        ) from exc
    except OpenAIError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "ai_provider_error", "message": "AI roadmap generation failed"},
        ) from exc

    try:
        db.query(RoadmapStep).filter(RoadmapStep.user_id == user.id).delete(
            synchronize_session=False
        )
        roadmap = [
            RoadmapStep(user_id=user.id, title=step["title"], content=step["content"], step_number=step["step_number"])
            for step in steps
        ]
        db.add_all(roadmap)
        db.commit()
        for step in roadmap:
            db.refresh(step)
        return [
            {
                "id": str(step.id),
                "step_number": step.step_number,
                "title": step.title,
                "content": step.content,
                "is_completed": step.is_completed,
            }
            for step in roadmap
        ]
    except Exception:
        db.rollback()
        raise


@router.post("/cv", response_model=CVResponse)
def generate_cv(
    request: CVRequest,
    _: User = Depends(get_current_user),
    __: None = Depends(enforce_ai_rate_limit),
) -> CVResponse:
    """Translate or normalize CV content using the server-side AI credential."""
    try:
        result = AIService(get_settings()).generate_cv(
            request.data, request.language, request.operation
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="CV AI is not configured") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except OpenAIError as exc:
        raise HTTPException(status_code=502, detail="CV AI request failed") from exc
    return CVResponse(data=result, language=request.language, operation=request.operation)
