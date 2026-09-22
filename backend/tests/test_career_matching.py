import math

from app.services.career_matching import _s2, calculate_matches


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
