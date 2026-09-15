"""Hybrid AHP-SAW-ROC calculation primitives.

The service is deliberately independent from SQLAlchemy and FastAPI so it can
be used by API routes, import jobs, and tests with the JSON stored in
``CareerBenchmark``.  Scores are expected to be on the same scale as the
benchmark requirements (normally 0--10).
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose
from typing import Mapping, Sequence, TypedDict

CR_THRESHOLD = 0.10
DEFAULT_AHP_BLEND = 0.50
ROC_WEIGHTS_5 = (0.4567, 0.2567, 0.1567, 0.09, 0.04)
RI_TABLE: dict[int, float] = {
    1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24,
    7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49,
}


class BenchmarkCriterion(TypedDict, total=False):
    """JSON-friendly criterion definition used by :func:`calculate_hybrid`."""

    minimum: float
    maximum: float
    target: float
    direction: str


class BenchmarkInput(TypedDict, total=False):
    requirements: dict[str, BenchmarkCriterion]
    ahp_matrix: list[list[float]]
    roc_order: list[str]


@dataclass(frozen=True)
class AHPResult:
    weights: dict[str, float]
    lambda_max: float
    consistency_index: float
    consistency_ratio: float
    consistent: bool


@dataclass(frozen=True)
class CalculationResult:
    normalized: dict[str, float]
    ahp_weights: dict[str, float]
    roc_weights: dict[str, float]
    hybrid_weights: dict[str, float]
    match_percent: float
    gap_risk: float
    ahp_consistency_ratio: float
    used_roc_fallback: bool


def _normalise_weights(weights: Mapping[str, float]) -> dict[str, float]:
    total = sum(max(0.0, float(value)) for value in weights.values())
    if not weights or total <= 0:
        raise ValueError("weights must contain at least one positive value")
    return {key: max(0.0, float(value)) / total for key, value in weights.items()}


def min_max_normalize(
    value: float,
    minimum: float,
    maximum: float,
    *,
    benefit: bool = True,
) -> float:
    """Return a bounded 0..1 min-max score (reverse the scale for costs)."""

    if maximum < minimum:
        raise ValueError("maximum must be greater than or equal to minimum")
    if isclose(maximum, minimum):
        return 1.0 if value >= maximum else 0.0
    result = (float(value) - minimum) / (maximum - minimum)
    if not benefit:
        result = 1.0 - result
    return max(0.0, min(1.0, result))


def roc_weights(order: Sequence[str]) -> dict[str, float]:
    """Calculate rank-order centroid weights, from highest to lowest rank."""

    names = list(dict.fromkeys(order))
    if not names:
        raise ValueError("roc order must not be empty")
    count = len(names)
    return {name: sum(1.0 / position for position in range(rank, count + 1)) / count
            for rank, name in enumerate(names, 1)}


def ahp_weights(
    matrix: Sequence[Sequence[float]],
    criteria: Sequence[str] | None = None,
) -> AHPResult:
    """Estimate an AHP priority vector and Saaty's consistency ratio."""

    n = len(matrix)
    if n == 0 or any(len(row) != n for row in matrix):
        raise ValueError("AHP matrix must be a non-empty square matrix")
    if any(value <= 0 for row in matrix for value in row):
        raise ValueError("AHP matrix values must be positive")
    names = list(criteria or (str(index) for index in range(n)))
    if len(names) != n:
        raise ValueError("criteria count must match AHP matrix size")

    # Geometric means are the standard practical approximation of the
    # principal eigenvector and avoid requiring NumPy in the API process.
    geometric = [sum(__import__("math").log(value) for value in row) / n for row in matrix]
    vector = _normalise_weights({str(i): __import__("math").exp(value) for i, value in enumerate(geometric)})
    values = list(vector.values())
    av = [sum(matrix[row][column] * values[column] for column in range(n)) for row in range(n)]
    lambda_max = sum(av[index] / values[index] for index in range(n)) / n
    ci = (lambda_max - n) / (n - 1) if n > 2 else 0.0
    ri = RI_TABLE.get(n, 1.49)
    cr = ci / ri if ri else 0.0
    return AHPResult(
        weights={name: vector[str(index)] for index, name in enumerate(names)},
        lambda_max=lambda_max,
        consistency_index=ci,
        consistency_ratio=cr,
        consistent=cr <= CR_THRESHOLD,
    )


def calculate_hybrid(
    scores: Mapping[str, float],
    benchmark: BenchmarkInput | Mapping[str, object],
    *,
    ahp_blend: float = DEFAULT_AHP_BLEND,
    cr_threshold: float = CR_THRESHOLD,
) -> CalculationResult:
    """Calculate normalized scores, hybrid weights, SAW match, and GAP risk."""

    if not 0.0 <= ahp_blend <= 1.0:
        raise ValueError("ahp_blend must be between 0 and 1")
    requirements = benchmark.get("requirements", {})  # type: ignore[union-attr]
    if not isinstance(requirements, Mapping):
        raise ValueError("benchmark requirements must be a mapping")
    names = list(scores)
    normalized: dict[str, float] = {}
    gaps: dict[str, float] = {}
    for name in names:
        raw = requirements.get(name, {})
        spec = raw if isinstance(raw, Mapping) else {}
        minimum = float(spec.get("minimum", 0.0))
        maximum = float(spec.get("maximum", spec.get("target", 10.0)))
        target = float(spec.get("target", maximum))
        benefit = str(spec.get("direction", "benefit")).lower() != "cost"
        normalized[name] = min_max_normalize(float(scores[name]), minimum, maximum, benefit=benefit)
        gaps[name] = max(0.0, (target - float(scores[name])) / target) if target > 0 and benefit else 0.0

    matrix = benchmark.get("ahp_matrix", [])  # type: ignore[union-attr]
    ahp = ahp_weights(matrix, names) if matrix else None
    order = benchmark.get("roc_order", names)  # type: ignore[union-attr]
    roc = roc_weights([str(item) for item in order])
    roc = {name: roc.get(name, 0.0) for name in names}
    roc = _normalise_weights(roc)
    use_fallback = ahp is None or ahp.consistency_ratio > cr_threshold
    ahp_map = ahp.weights if ahp and ahp.consistency_ratio <= cr_threshold else roc
    hybrid = _normalise_weights({name: ahp_blend * ahp_map.get(name, 0.0) + (1 - ahp_blend) * roc[name] for name in names})
    match = sum(normalized[name] * hybrid[name] for name in names) * 100.0
    risk = (sum(hybrid[name] * gaps[name] ** 2 for name in names) ** 0.5) * 100.0
    return CalculationResult(normalized, ahp_map, roc, hybrid, match, risk, ahp.consistency_ratio if ahp else 0.0, use_fallback)


# Explicit helpers/aliases make the calculation primitives convenient for API
# callers while keeping the main calculation in one place.
calculate_roc_weights = roc_weights
calculate_ahp_weights = ahp_weights


def calculate_saw_match(normalized: Mapping[str, float], weights: Mapping[str, float]) -> float:
    """Return a weighted SAW score as a percentage."""

    if set(normalized) != set(weights):
        raise ValueError("normalized scores and weights must have the same criteria")
    return sum(float(normalized[key]) * float(weights[key]) for key in weights) * 100.0


def calculate_gap_risk(
    scores: Mapping[str, float],
    requirements: Mapping[str, BenchmarkCriterion],
    weights: Mapping[str, float],
) -> float:
    """Return the weighted percentage of unmet (benefit) target requirements."""

    risk = 0.0
    for name, weight in weights.items():
        spec = requirements.get(name, {})
        target = float(spec.get("target", spec.get("maximum", 0.0)))
        if target > 0 and str(spec.get("direction", "benefit")).lower() != "cost":
            risk += max(0.0, (target - float(scores.get(name, 0.0))) / target) * float(weight)
    return risk * 100.0
