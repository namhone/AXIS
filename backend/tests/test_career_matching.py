import math

from app.services.career_matching import _s2


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
