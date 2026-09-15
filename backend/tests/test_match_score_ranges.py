import math

from app.services.career_matching import calculate_matches


def test_match_score_ranges_are_bounded():
    profile = {
        "gpa10": 8.7,
        "gpa11": 8.5,
        "gpa12": 8.9,
        "score10Math": 9.0,
        "score11Math": 9.2,
        "score12Math": 9.0,
        "score10Physics": 8.7,
        "score11Physics": 8.8,
        "score12Physics": 8.4,
        "score10English": 8.5,
        "score11English": 8.6,
        "score12English": 8.7,
        "ielts": 7.5,
        "interests": "khoa học, lập trình, dữ liệu và nghiên cứu",
        "personality": "sáng tạo, phân tích, làm việc nhóm",
        "activityRole": "trưởng ban kỹ thuật",
        "activityImpact": "quốc gia, dự án 500 người",
    }

    ranked = calculate_matches(profile)
    assert ranked["results"]

    for item in ranked["results"]:
        assert 0.0 <= item["score"] <= 100.0
        assert math.isfinite(item["score"])
