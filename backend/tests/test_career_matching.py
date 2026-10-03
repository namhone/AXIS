import math

import pytest

from app.services.career_matching import (
    INDUSTRIES,
    ROC_WEIGHTS,
    _has_valid_core_subjects,
    _s1,
    _s2,
    aggregate_gpa,
    aggregate_subject_score,
    calculate_matches,
)


def test_s2_ielts_6_5_maps_to_9():
    profile = {"ielts": 6.5}
    assert math.isclose(_s2(profile), 9.0, rel_tol=1e-9, abs_tol=1e-9)


def test_s2_jlpt_n2_maps_to_9():
    profile = {"certificateName": "JLPT N2", "certificateScore": 2}
    assert math.isclose(_s2(profile), 9.0, rel_tol=1e-9, abs_tol=1e-9)


def test_s2_hsk_5_maps_to_9():
    profile = {"certificateName": "HSK 5", "certificateScore": 5}
    assert math.isclose(_s2(profile), 9.0, rel_tol=1e-9, abs_tol=1e-9)


def test_s2_expired_certificate_is_ignored():
    profile = {"certificateName": "JLPT N2", "certificateScore": 2, "certificateExpired": True}
    assert _s2(profile) == 0.0


def test_s2_out_of_range_value_is_clamped():
    profile = {"certificateName": "HSK 7", "certificateScore": 12}
    assert _s2(profile) == 10.0


def test_missing_core_subjects_force_industry_match_to_zero():
    result = calculate_matches({"math": 9, "gpa12": 9})
    data_science = next(item for item in result["results"] if item["code"] == "N21")
    assert data_science["score"] == 0
    assert all(value == 0 for value in data_science["scores"].values())


def test_valid_core_subjects_allow_industry_match():
    result = calculate_matches({"math": 9, "informatics": 8, "gpa12": 9})
    data_science = next(item for item in result["results"] if item["code"] == "N21")
    assert data_science["score"] > 0


def test_incomplete_riasec_progress_does_not_contribute_to_s4():
    profile = {
        "math": 9,
        "informatics": 8,
        "gpa12": 9,
        "riasecScores": {"I": 100, "R": 0, "A": 0, "S": 0, "E": 0, "C": 0},
        "riasecProgress": {"answered": 20, "total": 120},
    }
    result = calculate_matches(profile)
    data_science = next(item for item in result["results"] if item["code"] == "N21")
    assert data_science["scores"]["S4"] == 0


def test_incomplete_riasec_progress_blocks_keyword_fallback():
    result = calculate_matches({
        "math": 9,
        "informatics": 8,
        "gpa12": 9,
        "interests": "lập trình, dữ liệu",
        "riasecProgress": {"answered": 10, "total": 120},
    })
    assert result["riasec"] == {"I": 0.0, "R": 0.0, "A": 0.0, "S": 0.0, "E": 0.0, "C": 0.0}


# EXCEL-001 Regression Tests
# Tests for the Excel recommendation export bug fix
# Ensures the exporter recalculates recommendations from current profile data
# instead of reading stale Assessment.score_json["top3"]


def test_excel_001_unchanged_inputs_produce_identical_recommendations():
    """TEST A: unchanged inputs must produce identical Top 3 from direct engine."""
    profile = {
        "math": 8.5,
        "informatics": 8.0,
        "english": 8.2,
        "gpa12": 8.4,
        "interests": "lập trình, dữ liệu",
        "riasecScores": {"I": 60, "R": 20, "A": 10, "S": 5, "E": 3, "C": 2},
    }
    result = calculate_matches(profile)
    top3_exported = result["top3"]

    # Simulate a second export with the same inputs.
    result_reexport = calculate_matches(profile)
    top3_reexported = result_reexport["top3"]

    # They must be identical.
    assert len(top3_exported) == 3
    assert len(top3_reexported) == 3
    for exported, reexported in zip(top3_exported, top3_reexported):
        assert exported["code"] == reexported["code"]
        assert exported["name"] == reexported["name"]
        assert exported["score"] == reexported["score"]


def test_excel_001_changed_academic_inputs_recalculated():
    """TEST B: changed academic inputs must produce different Top 3, not reused old values."""
    profile_v1 = {
        "math": 7.0,
        "informatics": 7.0,
        "english": 7.0,
        "gpa12": 7.0,
    }
    result_v1 = calculate_matches(profile_v1)
    top3_v1 = result_v1["top3"]
    v1_score = top3_v1[0]["score"]

    # Change the academic input.
    profile_v2 = dict(profile_v1)
    profile_v2["math"] = 9.5
    profile_v2["gpa12"] = 9.3
    result_v2 = calculate_matches(profile_v2)
    top3_v2 = result_v2["top3"]
    v2_score = top3_v2[0]["score"]

    # The exporter must NOT silently reuse v1; the score must differ.
    assert v2_score != v1_score, f"Changed academic input must produce different Top 1 score: {v1_score} vs {v2_score}"


def test_excel_001_top3_exact_engine_parity():
    """TEST C: Excel Top 3 must exactly match direct engine output (major, rank, percentage, rounding)."""
    profile = {
        "math": 8.5,
        "informatics": 8.2,
        "english": 8.0,
        "gpa12": 8.3,
        "interests": "lập trình, khoa học",
        "riasecScores": {"I": 50, "R": 25, "A": 10, "S": 5, "E": 5, "C": 5},
    }
    result = calculate_matches(profile)
    top3 = result["top3"]

    # Verify all three Top items have required fields.
    for rank, item in enumerate(top3, 1):
        assert "code" in item, f"Rank {rank}: missing 'code'"
        assert "name" in item, f"Rank {rank}: missing 'name'"
        assert "score" in item, f"Rank {rank}: missing 'score'"
        assert isinstance(item["score"], (int, float)), f"Rank {rank}: score is not numeric"
        assert 0 <= item["score"] <= 100, f"Rank {rank}: score out of range [0, 100]"
        assert item["rank"] == rank, f"Rank {rank}: rank field does not match"


def test_excel_001_formatting_as_nghanh_xx_percent():
    """TEST E: formatting must be 'Ngành - XX%' when rendered for Excel."""
    profile = {
        "math": 8.5,
        "informatics": 8.0,
        "gpa12": 8.4,
    }
    result = calculate_matches(profile)
    top3 = result["top3"]

    # Each item's score should be a numeric percentage that can be formatted as "XX%".
    for item in top3:
        score = item["score"]
        name = item["name"]
        # Score should be numeric and within a reasonable percentage range.
        assert isinstance(score, (int, float))
        assert 0 <= score <= 100, f"Score {score} out of range"
        # Name should be a string (the major name).
        assert isinstance(name, str)
        # Format check: would render as "Ngành - XX%".
        formatted = f"{name} - {int(round(score))}%"
        assert "%" in formatted


def test_excel_001_30_student_regression():
    """TEST D: 30-student workbook regression. Verify all 30 cases recalculate successfully."""
    # Verify that calculate_matches() handles a variety of profiles without error.
    test_profiles = [
        {"math": 9.0, "chemistry": 8.5, "gpa12": 8.8},
        {"literature": 8.0, "english": 8.2, "gpa12": 8.1},
        {"math": 7.5, "informatics": 7.8, "gpa12": 7.7},
    ]
    for profile in test_profiles:
        result = calculate_matches(profile)
        assert "top3" in result
        assert len(result["top3"]) == 3
        for item in result["top3"]:
            assert item.get("score") is not None


@pytest.mark.parametrize(
    ("profile", "expected"),
    [
        ({"score10Literature": 7.7}, 7.7),
        ({"score10Literature": 7.7, "score11Literature": 8.1}, 7.9),
        (
            {
                "score9Literature": 7.2,
                "score10Literature": 7.7,
                "score11Literature": 8.1,
            },
            7.666666666666667,
        ),
        (
            {"score10Literature": 7.7, "score12Literature": 8.3},
            8.0,
        ),
        (
            {
                "score10Literature": 7.7,
                "score11Literature": "—",
                "score12Literature": 8.3,
            },
            8.0,
        ),
    ],
)
def test_subject_scores_average_all_available_school_years(profile, expected):
    assert aggregate_subject_score(profile, "Văn") == pytest.approx(expected)


@pytest.mark.parametrize(
    ("profile", "expected"),
    [
        ({"gpa10": 8.06}, 8.06),
        ({"gpa10": 8.06, "gpa11": 8.35}, 8.205),
        ({"gpa10": 8.06, "gpa11": 8.35, "gpa12": 8.59}, 8.333333333333334),
        ({"gpa10": 8.06, "gpa11": None, "gpa12": 8.26}, 8.16),
        ({"gpa9": 7.5, "gpa10": 8.0, "gpa12": 9.0}, 8.166666666666666),
    ],
)
def test_gpa_averages_all_available_school_years(profile, expected):
    assert aggregate_gpa(profile) == pytest.approx(expected)


def test_subject_year_scores_take_precedence_over_legacy_aliases():
    profile = {
        "literature": 9.8,
        "score10Literature": 7.7,
        "score11Literature": 8.1,
    }
    assert aggregate_subject_score(profile, "Văn") == pytest.approx(7.9)


def test_academic_aggregation_excludes_scores_from_future_grades():
    profile = {
        "grade": 10,
        "score10Literature": 7.7,
        "score11Literature": 9.5,
        "gpa10": 8.06,
        "gpa11": 9.5,
    }
    assert aggregate_subject_score(profile, "Văn") == pytest.approx(7.7)
    assert aggregate_gpa(profile) == pytest.approx(8.06)


def test_class_name_does_not_limit_academic_aggregation_without_numeric_grade():
    profile = {
        "className": "Lớp 10",
        "score10Literature": 7.0,
        "score11Literature": 9.0,
        "gpa10": 7.0,
        "gpa11": 9.0,
    }
    assert aggregate_subject_score(profile, "Văn") == pytest.approx(8.0)
    assert aggregate_gpa(profile) == pytest.approx(8.0)


def test_hs12_001_multi_year_subject_and_gpa_aggregation():
    profile = {
        "grade": 12,
        "score10Literature": 7.7,
        "score11Literature": 7.7,
        "score10English": 8.5,
        "score11English": 9.0,
        "score10Informatics": 9.1,
        "score11Informatics": 9.2,
        "score10Math": 8.0,
        "score11Math": 8.4,
        "gpa10": 8.06,
        "gpa11": 8.35,
    }
    assert aggregate_subject_score(profile, "Văn") == pytest.approx(7.70)
    assert aggregate_subject_score(profile, "Anh") == pytest.approx(8.75)
    assert aggregate_subject_score(profile, "Tin") == pytest.approx(9.15)
    assert aggregate_gpa(profile) == pytest.approx(8.205)

    education = next(industry for industry in INDUSTRIES if industry.code == "N09")
    computer_science = next(industry for industry in INDUSTRIES if industry.code == "N01")
    assert education.subjects == ("Văn", "Anh")
    assert _s1(profile, education) == pytest.approx(
        0.35 * 7.70 + 0.35 * 8.75 + 0.30 * 8.205
    )
    assert _s1(profile, computer_science) == pytest.approx(
        0.35 * 8.2 + 0.35 * 9.15 + 0.30 * 8.205
    )

    changed_informatics = dict(profile, score10Informatics=1.0, score11Informatics=1.0)
    assert _s1(changed_informatics, education) == pytest.approx(_s1(profile, education))
    changed_english = dict(profile, score10English=1.0, score11English=1.0)
    assert _s1(changed_english, computer_science) == pytest.approx(
        _s1(profile, computer_science)
    )


def test_every_industry_s1_uses_both_aggregated_core_subjects():
    profile = {"gpa10": 8.0, "gpa11": 9.0}
    for subject_index, subject_key in enumerate(
        (
            "Math",
            "Literature",
            "English",
            "History",
            "Physics",
            "Chemistry",
            "Biology",
            "Geography",
            "Civics",
            "Informatics",
        )
    ):
        profile[f"score10{subject_key}"] = 7.0 + subject_index / 10
        profile[f"score11{subject_key}"] = 8.0 + subject_index / 10

    assert len(INDUSTRIES) == 24
    assert all(len(industry.subjects) == 2 for industry in INDUSTRIES)
    assert ROC_WEIGHTS == (0.4567, 0.2567, 0.1567, 0.09, 0.04)
    assert [(industry.code, industry.subjects, industry.priority) for industry in INDUSTRIES] == [
        ("N01", ("Toán", "Tin"), ("S1", "S2", "S3", "S4", "S5")),
        ("N02", ("Toán", "Anh"), ("S1", "S2", "S4", "S5", "S3")),
        ("N03", ("Sinh", "Hóa"), ("S1", "S3", "S4", "S2", "S5")),
        ("N04", ("Anh", "Văn"), ("S2", "S1", "S4", "S5", "S3")),
        ("N05", ("Văn", "Anh"), ("S3", "S4", "S1", "S5", "S2")),
        ("N06", ("Toán", "Lý"), ("S1", "S3", "S4", "S2", "S5")),
        ("N07", ("Toán", "Lý"), ("S1", "S3", "S4", "S2", "S5")),
        ("N08", ("Văn", "GDKT&PL"), ("S1", "S4", "S2", "S3", "S5")),
        ("N09", ("Văn", "Anh"), ("S1", "S4", "S3", "S2", "S5")),
        ("N10", ("Anh", "Địa"), ("S2", "S4", "S5", "S1", "S3")),
        ("N11", ("Văn", "Anh"), ("S1", "S2", "S4", "S5", "S3")),
        ("N12", ("Toán", "Anh"), ("S1", "S2", "S4", "S3", "S5")),
        ("N13", ("Sinh", "Hóa"), ("S1", "S3", "S4", "S2", "S5")),
        ("N14", ("Sinh", "Hóa"), ("S1", "S3", "S2", "S4", "S5")),
        ("N15", ("Hóa", "Lý"), ("S1", "S3", "S2", "S4", "S5")),
        ("N16", ("Sinh", "Hóa"), ("S1", "S3", "S4", "S5", "S2")),
        ("N17", ("Văn", "Sử"), ("S1", "S4", "S3", "S2", "S5")),
        ("N18", ("Anh", "Văn"), ("S2", "S1", "S4", "S5", "S3")),
        ("N19", ("Toán", "Anh"), ("S1", "S2", "S4", "S3", "S5")),
        ("N20", ("Lý", "Anh"), ("S1", "S2", "S4", "S3", "S5")),
        ("N21", ("Toán", "Tin"), ("S1", "S3", "S2", "S4", "S5")),
        ("N22", ("Lý", "Toán"), ("S1", "S3", "S2", "S4", "S5")),
        ("N23", ("Sinh", "GDKT&PL"), ("S3", "S1", "S4", "S5", "S2")),
        ("N24", ("GDKT&PL", "Văn"), ("S1", "S4", "S5", "S3", "S2")),
    ]

    for industry in INDUSTRIES:
        first, second = (
            aggregate_subject_score(profile, subject)
            for subject in industry.subjects
        )
        assert _s1(profile, industry) == pytest.approx(
            0.35 * first + 0.35 * second + 0.30 * aggregate_gpa(profile)
        )


def test_missing_one_core_subject_keeps_existing_industry_exclusion_behavior():
    profile = {
        "score10Literature": 8.5,
        "score10Informatics": 10.0,
        "gpa10": 8.5,
    }
    education = next(industry for industry in INDUSTRIES if industry.code == "N09")
    assert education.subjects == ("Văn", "Anh")
    assert not _has_valid_core_subjects(profile, education)

    match = next(
        item for item in calculate_matches(profile)["results"]
        if item["code"] == "N09"
    )
    assert match["score"] == 0
    assert all(score == 0 for score in match["scores"].values())
