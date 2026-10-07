import pytest

from app.services.calculation_engine import (
    ahp_weights,
    calculate_hybrid,
    min_max_normalize,
    roc_weights,
)


def test_normalization_clamps_benefit_and_reverses_cost():
    assert min_max_normalize(5, 0, 10) == pytest.approx(0.5)
    assert min_max_normalize(-1, 0, 10) == 0
    assert min_max_normalize(11, 0, 10) == 1
    assert min_max_normalize(5, 0, 10, benefit=False) == pytest.approx(0.5)
    assert min_max_normalize(2, 2, 2) == 1
    assert min_max_normalize(1, 2, 2) == 0


def test_ahp_and_roc_weights_are_normalized_and_consistency_is_reported():
    matrix = [
        [1, 2, 4],
        [0.5, 1, 2],
        [0.25, 0.5, 1],
    ]
    ahp = ahp_weights(matrix, ["S1", "S2", "S3"])
    roc = roc_weights(["S1", "S2", "S3"])

    assert sum(ahp.weights.values()) == pytest.approx(1)
    assert ahp.consistency_ratio == pytest.approx(0)
    assert ahp.consistent
    assert sum(roc.values()) == pytest.approx(1)
    assert roc["S1"] > roc["S2"] > roc["S3"]


def test_hybrid_weights_and_score_are_reproducible_and_input_sensitive():
    benchmark = {
        "requirements": {
            key: {"minimum": 0, "maximum": 10, "target": target}
            for key, target in zip(("S1", "S2", "S3", "S4", "S5"), (8, 7, 6, 5, 4))
        },
        "roc_order": ["S1", "S2", "S3", "S4", "S5"],
        "ahp_matrix": [],
    }
    scores = {"S1": 8, "S2": 7, "S3": 6, "S4": 5, "S5": 4}
    first = calculate_hybrid(scores, benchmark)
    repeated = calculate_hybrid(scores, benchmark)
    changed = calculate_hybrid({**scores, "S4": 9}, benchmark)

    assert first == repeated
    assert first.used_roc_fallback
    assert sum(first.hybrid_weights.values()) == pytest.approx(1)
    assert first.match_percent == pytest.approx(70.0, abs=0.02)
    assert 0 <= first.gap_risk <= 100
    assert changed.match_percent > first.match_percent


def test_inconsistent_ahp_uses_roc_fallback():
    matrix = [
        [1, 9, 1 / 9],
        [1 / 9, 1, 9],
        [9, 1 / 9, 1],
    ]
    result = ahp_weights(matrix, ["S1", "S2", "S3"])
    assert not result.consistent
    assert result.consistency_ratio > 0.1
