from typing import Any
import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from ..deps import get_current_user
from ...core.database import get_db
from ...models.profile import Profile
from ...models.user import User

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


class ProfileUpdate(BaseModel):
    """Profile fields are intentionally open-ended for frontend compatibility.
    
    Accepts both flat fields and nested CV data. Extra fields are preserved.
    """

    model_config = ConfigDict(extra="allow")

    subject: str | None = Field(default=None, max_length=255)
    examSubject: str | None = Field(default=None, max_length=255)
    
    # CV Builder fields - all optional and flexible
    name: str | None = None
    role: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    location: str | None = None
    summary: str | None = None
    skills: list[str] | None = None
    interests: list[str] | None = None
    certificates: list[str] | None = None
    project: dict[str, Any] | None = None
    activity: dict[str, Any] | None = None
    education: dict[str, Any] | None = None
    achievement: dict[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_subject_fields(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        values = dict(value)
        exam_subject = values.get("examSubject")
        subject = values.get("subject")
        # examSubject is the newer name, but accept the original subject key.
        if isinstance(exam_subject, str):
            exam_subject = exam_subject.strip() or None
        if isinstance(subject, str):
            subject = subject.strip() or None
        canonical = exam_subject if exam_subject is not None else subject
        values["examSubject"] = canonical
        values["subject"] = canonical
        return values


def _normalize_score_values(data: dict[str, Any]) -> dict[str, Any]:
    """Keep school scores within the 0-10 scale at the API boundary."""
    normalized = dict(data)
    for key, value in list(normalized.items()):
        is_subject = re.fullmatch(r"score(?:9|10|11|12)[A-Za-z]+", key)
        is_gpa = re.fullmatch(r"gpa(?:9|10|11|12)", key)
        if not (is_subject or is_gpa or key == "highSchoolLanguageScore"):
            continue
        try:
            parsed = float(str(value).strip().replace(",", "."))
            normalized[key] = round(min(10.0, max(0.0, parsed)), 1)
        except (TypeError, ValueError):
            normalized[key] = ""
    if "entranceScore" in normalized:
        try:
            parsed = float(str(normalized["entranceScore"]).strip().replace(",", "."))
            normalized["entranceScore"] = round(min(30.0, max(0.0, parsed)), 2)
        except (TypeError, ValueError):
            normalized["entranceScore"] = ""
    if "certificateName" in normalized and normalized.get("certificateName") == "IELTS":
        try:
            parsed = float(str(normalized.get("certificateScore", "")).strip().replace(",", "."))
            normalized["certificateScore"] = round(parsed, 1) if 0 <= parsed <= 9 else ""
        except (TypeError, ValueError):
            normalized["certificateScore"] = ""
    return normalized


def _canonical_subject(data: dict[str, Any], stored_subject: str | None = None) -> str | None:
    """Read both subject spellings while keeping legacy records usable."""

    value = stored_subject or data.get("examSubject") or data.get("subject")
    if not isinstance(value, str):
        return None
    return value.strip() or None


@router.get("")
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    profile = db.get(Profile, user.id)
    data = dict(profile.data) if profile else {}
    subject = _canonical_subject(data, profile.subject if profile else None)
    if subject:
        data["examSubject"] = subject
        data["subject"] = subject
    data["name"] = user.full_name
    data["email"] = user.email
    return data


@router.put("")
def update_profile(
    payload: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile = db.get(Profile, user.id)
    data = dict(profile.data) if profile else {}
    
    # Merge payload into profile data, preserving nested CV structures
    payload_dict = payload.model_dump(exclude_unset=True)
    data.update(_normalize_score_values(payload_dict))
    
    # Preserve user's identity
    data["name"] = user.full_name
    data["email"] = user.email
    subject = payload.examSubject or payload.subject or _canonical_subject(data)
    data["examSubject"] = subject
    data["subject"] = subject
    
    if profile is None:
        profile = Profile(user_id=user.id, data=data, subject=subject)
        db.add(profile)
    else:
        profile.data = data
        profile.subject = subject
    db.commit()
    return get_profile(user, db)
