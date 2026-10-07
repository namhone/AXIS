import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from openai import OpenAIError
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from ..deps import get_current_user
from ...core.config import get_settings
from ...core.database import get_db
from ...models.learning import Assessment, Goal, RoadmapStep
from ...models.profile import Profile
from ...models.user import User
from ...services.ai import AIService
from ...services.skill_planner import assessment_career_matches, build_skill_plan, selected_career_context
from ...services.schedule import normalize_week
from ...core.rate_limit import LockoutRateLimiter, SlidingWindowRateLimiter

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])
_ai_limiter = SlidingWindowRateLimiter(
    limit=get_settings().ai_rate_limit_requests,
    window_seconds=get_settings().ai_rate_limit_window_seconds,
)
_cv_ai_limiter = LockoutRateLimiter(limit=5, window_seconds=600, lockout_seconds=600)


class CVRequest(BaseModel):
    data: dict[str, object] = Field(...)
    language: str = Field(pattern="^(vi|en)$")
    operation: str = Field(default="translate", pattern="^(translate|normalize)$")

    @model_validator(mode="after")
    def validate_data_size(self):
        if len(json.dumps(self.data, ensure_ascii=False)) > 16000:
            raise ValueError("CV content is too large")
        return self


class CVResponse(BaseModel):
    data: dict[str, object]
    language: str
    operation: str


class RiasecEvaluationRequest(BaseModel):
    scores: dict[str, float]
    aspect_scores: dict[str, dict[str, float]]
    aspect_answered: dict[str, dict[str, int]]
    completion: int = Field(ge=0, le=100)

    @model_validator(mode="after")
    def validate_riasec_data(self):
        codes = {"R", "I", "A", "S", "E", "C"}
        aspects = {"1", "2", "3", "4", "5"}
        if set(self.scores) != codes or set(self.aspect_scores) != codes or set(self.aspect_answered) != codes:
            raise ValueError("All six RIASEC groups are required")
        if any(not 0 <= score <= 100 for score in self.scores.values()):
            raise ValueError("RIASEC scores must be between 0 and 100")
        for code in codes:
            if set(self.aspect_scores[code]) != aspects or set(self.aspect_answered[code]) != aspects:
                raise ValueError("All five aspects are required for each RIASEC group")
            if any(not 0 <= score <= 100 for score in self.aspect_scores[code].values()):
                raise ValueError("Aspect scores must be between 0 and 100")
            if any(not 0 <= answered <= 2 for answered in self.aspect_answered[code].values()):
                raise ValueError("Aspect answered counts must be between 0 and 2")
        expected_completion = round(
            sum(count for group in self.aspect_answered.values() for count in group.values()) / 60 * 100
        )
        if self.completion != expected_completion:
            raise ValueError("RIASEC completion does not match answered counts")
        return self


def enforce_ai_rate_limit(
    request: Request,
    user: User = Depends(get_current_user),
) -> None:
    _ai_limiter.check(f"{user.id}:{request.client.host if request.client else 'unknown'}")


def enforce_cv_ai_rate_limit(
    request: Request,
    user: User = Depends(get_current_user),
) -> None:
    _cv_ai_limiter.check(f"{user.id}:{request.client.host if request.client else 'unknown'}")


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
    profile_data.pop("customCareerFocus", None)
    career_matches = assessment_career_matches(latest_assessment)
    profile_data["career_matches"] = career_matches
    profile_data["career_focus"] = {
        "recommended": career_matches,
        "selected": selected_career_context(goals),
    }
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
    __: None = Depends(enforce_cv_ai_rate_limit),
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


@router.post("/riasec-evaluation", response_model=None)
def evaluate_riasec(
    payload: RiasecEvaluationRequest,
    _: User = Depends(get_current_user),
    __: None = Depends(enforce_ai_rate_limit),
) -> dict[str, str]:
    if payload.completion < 60:
        raise HTTPException(status_code=422, detail="At least 60% of the questionnaire must be answered")
    holland_code = "".join(sorted(payload.scores, key=lambda code: (-payload.scores[code], code))[:3])
    try:
        return AIService(get_settings()).evaluate_riasec(
            scores=payload.scores,
            aspect_scores=payload.aspect_scores,
            aspect_answered=payload.aspect_answered,
            holland_code=holland_code,
            completion=payload.completion,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "ai_unavailable", "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "ai_invalid_response", "message": "AI returned an invalid RIASEC evaluation"},
        ) from exc
    except OpenAIError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "ai_provider_error", "message": "AI RIASEC evaluation failed"},
        ) from exc
