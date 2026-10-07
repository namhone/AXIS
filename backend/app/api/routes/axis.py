from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from ..deps import get_current_user
from ...core.database import get_db
from ...models.axis import CareerBenchmark, CompetencyScore, MatchLog
from ...models.user import User
from ...services.calculation_engine import calculate_hybrid
from ...services.career_matching import INDUSTRIES

router = APIRouter(prefix="/api/v1/axis", tags=["axis"])


class AxisEvaluatePayload(BaseModel):
    scores: dict[str, Annotated[float, Field(ge=0, le=10)]] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def validate_score_keys(self):
        if set(self.scores) != {"S1", "S2", "S3", "S4", "S5"}:
            raise ValueError("scores must contain S1, S2, S3, S4 and S5")
        return self


def _benchmark(industry: Any) -> dict[str, Any]:
    targets_by_rank = (8.5, 7.5, 6.5, 5.5, 5.0)
    priority = list(industry.priority)
    requirements = {
        criterion: {
            "minimum": 0,
            "maximum": 10,
            "target": targets_by_rank[index],
        }
        for index, criterion in enumerate(priority)
    }
    return {
        "code": industry.code,
        "name": industry.name,
        "requirements": requirements,
        "roc_order": priority,
        "ahp_matrix": [],
        "subjects": list(industry.subjects),
        "riasec": list(industry.riasec),
    }


def _seed_benchmarks(db: Session) -> None:
    existing = {row.code for row in db.query(CareerBenchmark.code).all()}
    missing = [_benchmark(industry) for industry in INDUSTRIES if industry.code not in existing]
    if not missing:
        return
    db.add_all(
        [
            CareerBenchmark(
                code=item["code"],
                name=item["name"],
                requirements_json=item["requirements"],
                ahp_matrix_json=item["ahp_matrix"],
                roc_order_json=item["roc_order"],
            )
            for item in missing
        ]
    )
    db.commit()


@router.get("/benchmarks", response_model=None)
def list_benchmarks(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """Return the shared career catalog used by dashboard calculations."""

    _seed_benchmarks(db)
    industry_metadata = {industry.code: industry for industry in INDUSTRIES}
    rows = db.query(CareerBenchmark).order_by(CareerBenchmark.code).all()
    return [
        {
            "code": row.code,
            "name": industry_metadata[row.code].name,
            "requirements": row.requirements_json,
            "roc_order": row.roc_order_json,
            "ahp_matrix": row.ahp_matrix_json,
            "subjects": list(industry_metadata[row.code].subjects),
            "riasec": list(industry_metadata[row.code].riasec),
        }
        for row in rows
        if row.code in industry_metadata
    ]


@router.post("/evaluate", response_model=None)
def evaluate_axis(
    payload: AxisEvaluatePayload,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    scores = payload.scores
    _seed_benchmarks(db)
    industry_metadata = {industry.code: industry for industry in INDUSTRIES}
    benchmark_rows = db.query(CareerBenchmark).order_by(CareerBenchmark.code).all()
    results = []
    for row in benchmark_rows:
        industry = industry_metadata.get(row.code)
        if industry is None:
            continue
        benchmark = {
            "code": row.code,
            "name": row.name,
            "requirements": row.requirements_json,
            "ahp_matrix": row.ahp_matrix_json,
            "roc_order": row.roc_order_json,
        }
        result = calculate_hybrid(scores, benchmark)
        explanations = {
            key: {
                "score": scores[key],
                "normalized": round(result.normalized[key], 4),
                "weight": round(result.hybrid_weights[key], 4),
                "contribution": round(result.normalized[key] * result.hybrid_weights[key] * 100, 2),
                "target": float(row.requirements_json.get(key, {}).get("target", 10)),
            }
            for key in scores
        }
        results.append(
            {
                "code": row.code,
                "name": industry.name,
                "match_score": round(result.match_percent, 2),
                "gap_risk": round(result.gap_risk, 2),
                "normalized": result.normalized,
                "weights": result.hybrid_weights,
                "explanation": explanations,
                "ahp_consistency_ratio": round(result.ahp_consistency_ratio, 4),
                "used_roc_fallback": result.used_roc_fallback,
            }
        )
    normalized = {
        key: max(0.0, min(1.0, value / 10.0))
        for key, value in scores.items()
    }
    competency = CompetencyScore(
        user_id=user.id,
        s1=scores["S1"],
        s2=scores["S2"],
        s3=scores["S3"],
        s4=scores["S4"],
        s5=scores["S5"],
        normalized_json=normalized,
    )
    db.add(competency)
    db.flush()
    results.sort(key=lambda item: (-item["match_score"], item["code"]))
    for rank, item in enumerate(results, 1):
        item["rank"] = rank
    db.add(MatchLog(user_id=user.id, competency_score_id=competency.id, results_json={"results": results}))
    db.commit()
    return {"scores": scores, "results": results}
