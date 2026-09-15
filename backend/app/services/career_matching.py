from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


ROC_WEIGHTS = (0.4567, 0.2567, 0.1567, 0.09, 0.04)


@dataclass(frozen=True)
class Industry:
    code: str
    name: str
    subjects: tuple[str, str]
    riasec: tuple[str, str]
    priority: tuple[str, str, str, str, str]


INDUSTRIES = (
    Industry("N01", "Máy tính & CNTT", ("Toán", "Tin"), ("I", "R"), ("S1", "S2", "S3", "S4", "S5")),
    Industry("N02", "Kinh doanh & Quản lý", ("Toán", "Anh"), ("E", "C"), ("S1", "S2", "S4", "S5", "S3")),
    Industry("N03", "Y dược & Khoa học Sức khỏe", ("Sinh", "Hóa"), ("I", "S"), ("S1", "S3", "S4", "S2", "S5")),
    Industry("N04", "Ngôn ngữ, Văn hóa & Ngoại ngữ", ("Anh", "Văn"), ("A", "S"), ("S2", "S1", "S4", "S5", "S3")),
    Industry("N05", "Thiết kế, Mỹ thuật & Nghệ thuật", ("Văn", "Anh"), ("A", "R"), ("S3", "S4", "S1", "S5", "S2")),
    Industry("N06", "Kỹ thuật & Tự động hóa", ("Toán", "Lý"), ("R", "I"), ("S1", "S3", "S4", "S2", "S5")),
    Industry("N07", "Kiến trúc & Xây dựng", ("Toán", "Lý"), ("R", "A"), ("S1", "S3", "S4", "S2", "S5")),
    Industry("N08", "Luật & An ninh - Quốc phòng", ("Văn", "GDKT&PL"), ("E", "C"), ("S1", "S4", "S2", "S3", "S5")),
    Industry("N09", "Sư phạm & Giáo dục", ("Văn", "Anh"), ("S", "A"), ("S1", "S4", "S3", "S2", "S5")),
    Industry("N10", "Du lịch, Khách sạn & Nhà hàng", ("Anh", "Địa"), ("S", "E"), ("S2", "S4", "S5", "S1", "S3")),
    Industry("N11", "Truyền thông, Báo chí & MKT", ("Văn", "Anh"), ("A", "E"), ("S1", "S2", "S4", "S5", "S3")),
    Industry("N12", "Tài chính - Ngân hàng - Bảo hiểm", ("Toán", "Anh"), ("C", "E"), ("S1", "S2", "S4", "S3", "S5")),
    Industry("N13", "Môi trường & Tài nguyên", ("Sinh", "Hóa"), ("I", "R"), ("S1", "S3", "S4", "S2", "S5")),
    Industry("N14", "Bào chế & Công nghệ Sinh học", ("Sinh", "Hóa"), ("I", "R"), ("S1", "S3", "S2", "S4", "S5")),
    Industry("N15", "Hóa học & Công nghệ Vật liệu", ("Hóa", "Lý"), ("I", "R"), ("S1", "S3", "S2", "S4", "S5")),
    Industry("N16", "Nông - Lâm - Thủy sản", ("Sinh", "Hóa"), ("R", "I"), ("S1", "S3", "S4", "S5", "S2")),
    Industry("N17", "Khoa học Xã hội & Nhân văn", ("Văn", "Sử"), ("S", "I"), ("S1", "S4", "S3", "S2", "S5")),
    Industry("N18", "Quan hệ Quốc tế & Ngoại giao", ("Anh", "Văn"), ("E", "S"), ("S2", "S1", "S4", "S5", "S3")),
    Industry("N19", "Logistics & Chuỗi cung ứng", ("Toán", "Anh"), ("C", "E"), ("S1", "S2", "S4", "S3", "S5")),
    Industry("N20", "Hàng không & Hàng hải", ("Lý", "Anh"), ("R", "E"), ("S1", "S2", "S4", "S3", "S5")),
    Industry("N21", "Toán học & Khoa học Dữ liệu", ("Toán", "Tin"), ("I", "C"), ("S1", "S3", "S2", "S4", "S5")),
    Industry("N22", "Vật lý & Khoa học Vũ trụ", ("Lý", "Toán"), ("I", "R"), ("S1", "S3", "S2", "S4", "S5")),
    Industry("N23", "Thể dục, Thể thao & Quản lý TDTT", ("Sinh", "GDKT&PL"), ("R", "S"), ("S3", "S1", "S4", "S5", "S2")),
    Industry("N24", "Quản lý Nhà nước & Công tác Xã hội", ("GDKT&PL", "Văn"), ("S", "C"), ("S1", "S4", "S5", "S3", "S2")),
)

SUBJECT_KEYS = {
    "Toán": ("math", "toan", "mathScore", "toanScore", "score9Math", "score10Math", "score11Math", "score12Math"),
    "Tin": ("informatics", "tin", "informaticsScore", "tinScore", "score9Informatics", "score10Informatics", "score11Informatics", "score12Informatics"),
    "Anh": ("english", "anh", "englishScore", "anhScore", "score9English", "score10English", "score11English", "score12English"),
    "Văn": ("literature", "van", "literatureScore", "vanScore", "score9Literature", "score10Literature", "score11Literature", "score12Literature"),
    "Hóa": ("chemistry", "hoa", "chemistryScore", "hoaScore", "score9Chemistry", "score10Chemistry", "score11Chemistry", "score12Chemistry"),
    "Sinh": ("biology", "sinh", "biologyScore", "sinhScore", "score9Biology", "score10Biology", "score11Biology", "score12Biology"),
    "Lý": ("physics", "ly", "physicsScore", "lyScore", "score9Physics", "score10Physics", "score11Physics", "score12Physics"),
    "Địa": ("geography", "dia", "geographyScore", "diaScore", "score9Geography", "score10Geography", "score11Geography", "score12Geography"),
    "Sử": ("history", "su", "historyScore", "suScore", "score9History", "score10History", "score11History", "score12History"),
    "GDKT&PL": ("civics", "gdktpl", "civicsScore", "gdktplScore", "score9Civics", "score10Civics", "score11Civics", "score12Civics"),
}

RIASEC_KEYWORDS = {
    "I": ("nghiên cứu", "phân tích", "khoa học", "lập trình", "dữ liệu", "thí nghiệm"),
    "R": ("kỹ thuật", "thực hành", "máy móc", "xây dựng", "thể thao", "sửa chữa"),
    "A": ("thiết kế", "nghệ thuật", "viết", "sáng tạo", "truyền thông", "âm nhạc"),
    "S": ("giảng dạy", "tình nguyện", "hỗ trợ", "cộng đồng", "giao tiếp", "tư vấn"),
    "E": ("lãnh đạo", "kinh doanh", "bán hàng", "quản lý", "marketing", "đàm phán"),
    "C": ("tổ chức", "tài chính", "kế toán", "quản trị", "excel", "quy trình"),
}


def _number(value: Any) -> float | None:
    if value is None:
        return None
    match = re.search(r"\d+(?:[.,]\d+)?", str(value))
    if not match:
        return None
    return float(match.group().replace(",", "."))


def _clamp(value: float) -> float:
    return max(0.0, min(10.0, value))


def _gpa(profile: dict[str, Any]) -> float:
    values = [_number(profile.get(key)) for key in ("gpa10", "gpa11", "gpa12")]
    values = [value for value in values if value is not None]
    return _clamp(sum(values) / len(values)) if values else 0.0


def _subject_score(profile: dict[str, Any], subject: str) -> float | None:
    for key in SUBJECT_KEYS[subject]:
        value = _number(profile.get(key))
        if value is not None:
            return _clamp(value)
    return None


def _s1(profile: dict[str, Any], industry: Industry) -> float:
    first, second = (_subject_score(profile, subject) for subject in industry.subjects)
    gpa = _gpa(profile)
    if first is None and second is None:
        return gpa
    if first is None:
        return _clamp(second * 0.5 + gpa * 0.5) if second is not None else gpa
    if second is None:
        return _clamp(first * 0.5 + gpa * 0.5)
    return _clamp(first * 0.35 + second * 0.35 + gpa * 0.30)


def _score_language_certificate(cert_name: str | None, cert_score: Any, *, expired: bool = False) -> float:
    """Map a language certificate to the AXIS 0..10 scale.

    This intentionally validates the seven major certificate families used in the
    project: IELTS, TOEFL, HSK, JLPT, DELF/DALF, TOPIK, and Goethe/TestDaF.
    Inputs outside the valid range are clamped before matching, while expired
    certificates are ignored instead of being counted as an active strength.
    """
    if expired:
        return 0.0

    name = (cert_name or "").strip().lower()
    score = _number(cert_score)
    if not name and score is None:
        return 0.0

    if any(token in name for token in ("ielts", "toeic", "toeic")):
        value = max(0.0, min(9.0, float(score if score is not None else 0.0)))
        if value >= 8.5:
            return 10.0
        if value >= 7.0:
            return 9.0
        if value >= 6.5:
            return 9.0
        if value >= 5.5:
            return 6.5
        return 0.0

    if "toefl" in name:
        value = max(0.0, min(120.0, float(score if score is not None else 0.0)))
        if value >= 110: return 10.0
        if value >= 94: return 9.0
        if value >= 79: return 8.0
        if value >= 60: return 6.5
        return 0.0

    if "hsk" in name:
        level_match = re.search(r"hsk\s*(\d+)", name)
        level = int(level_match.group(1)) if level_match else None
        if level is not None:
            mapping = {1: 3.0, 2: 5.0, 3: 7.0, 4: 8.5, 5: 9.0, 6: 10.0, 7: 10.0}
            return mapping.get(level, 10.0 if level and level >= 7 else 0.0)
        if score is not None:
            clamped = max(0.0, min(10.0, float(score)))
            return 10.0 if clamped >= 6 else 9.0 if clamped >= 5 else 8.0 if clamped >= 4 else 6.5 if clamped >= 3 else 0.0
        return 0.0

    if "jlpt" in name:
        level_match = re.search(r"n([1-5])", name)
        if level_match:
            mapping = {"1": 10.0, "2": 9.0, "3": 7.0, "4": 5.0, "5": 3.0}
            return mapping.get(level_match.group(1), 0.0)
        if score is not None:
            return 10.0 if score >= 5 else 9.0 if score >= 4 else 7.0 if score >= 3 else 5.0 if score >= 2 else 0.0
        return 0.0

    if any(token in name for token in ("delf", "dalf")):
        level_match = re.search(r"(a1|a2|b1|b2|c1|c2)", name)
        mapping = {"a1": 3.0, "a2": 5.0, "b1": 7.0, "b2": 8.5, "c1": 9.0, "c2": 10.0}
        return mapping.get(level_match.group(1) if level_match else "", 0.0)

    if "topik" in name:
        level_match = re.search(r"(1|2|3|4|5|6|7)", name)
        mapping = {"1": 4.0, "2": 5.0, "3": 6.0, "4": 7.0, "5": 8.5, "6": 9.0, "7": 10.0}
        return mapping.get(level_match.group(1) if level_match else "", 0.0)

    if any(token in name for token in ("goethe", "testdaf")):
        if "c2" in name or "testdaf" in name and score is not None and score >= 16:
            return 10.0
        if "c1" in name or score is not None and score >= 13:
            return 9.0
        if score is not None and score >= 10:
            return 8.0
        return 0.0

    if "deutsch" in name or "german" in name:
        # This is a generic fallback for German proficiency certificates.
        return 9.0 if score is not None and score >= 6 else 0.0

    if score is not None:
        if score >= 8.5:
            return 10.0
        if score >= 7.0:
            return 9.0
        if score >= 6.5:
            return 9.0
        if score >= 5.5:
            return 6.5
    return 0.0


def _s2(profile: dict[str, Any]) -> float:
    scores: list[float] = []

    ielts = _number(profile.get("ielts"))
    toefl = _number(profile.get("toefl"))
    certificate_name = str(profile.get("certificateName", "") or "")
    certificate_score = _number(profile.get("certificateScore"))
    expired = bool(profile.get("certificateExpired")) or bool(profile.get("certificateIsExpired"))

    if ielts is not None:
        scores.append(_score_language_certificate("IELTS", ielts, expired=expired))
    if toefl is not None:
        scores.append(_score_language_certificate("TOEFL", toefl, expired=expired))
    if certificate_name:
        scores.append(_score_language_certificate(certificate_name, certificate_score, expired=expired))

    if not scores:
        return 0.0

    best = max(scores)
    bonus = max(0, sum(score >= 8 for score in scores) - 1) * 0.5
    return _clamp(best + bonus)


def _s3(profile: dict[str, Any], industry: Industry) -> float:
    rank = str(profile.get("awardRank", "") or profile.get("customAwardName", "")).lower()
    base = next((value for token, value in (("nhất", 10), ("nhì", 9.5), ("ba", 9), ("kk", 8.5)) if token in rank), 0.0)
    if not base:
        return 0.0
    scope = str(profile.get("examProvince", "") or profile.get("examType", "")).lower()
    multiplier = 1.3 if any(subject.lower() in str(profile.get("examDescription", "")).lower() for subject in industry.subjects) else 1.1 if scope else 1.0
    if any(token in scope for token in ("quốc gia", "quốc tế")):
        base = base
    elif any(token in scope for token in ("tỉnh", "thành phố")):
        base = max(0.0, base - 2)
    else:
        base = max(0.0, base - 5)
    return _clamp(base * multiplier)


def _riasec_scores(profile: dict[str, Any]) -> dict[str, float]:
    raw = profile.get("riasecScores")
    if isinstance(raw, dict):
        values = {code: _number(raw.get(code)) or 0 for code in RIASEC_KEYWORDS}
        total = sum(values.values())
        if total:
            return {code: value / total * 100 for code, value in values.items()}
    text = " ".join(str(profile.get(key, "")) for key in ("interests", "personality", "skills", "activityName", "activityRole", "projectType", "projectDescription")).lower()
    values = {code: 10.0 for code in RIASEC_KEYWORDS}
    for code, keywords in RIASEC_KEYWORDS.items():
        values[code] += sum(15 for keyword in keywords if keyword in text)
    total = sum(values.values())
    return {code: value / total * 100 for code, value in values.items()}


def _s4(profile: dict[str, Any], industry: Industry) -> float:
    scores = _riasec_scores(profile)
    return _clamp((scores[industry.riasec[0]] * 0.7 + scores[industry.riasec[1]] * 0.3) / 10)


def _s5(profile: dict[str, Any]) -> float:
    role = str(profile.get("activityRole", "")).lower()
    impact = str(profile.get("activityImpact", "")).lower()
    role_score = 6 if "trưởng" in role or "leader" in role else 4.5 if "ban" in role else 3 if role else 0
    scale_score = 3 if any(token in impact for token in ("tỉnh", "lớn", "200", "500")) else 2 if role else 1 if impact else 0
    multiplier = 1.2 if any(token in (str(profile.get("activityName", "")) + str(profile.get("activityImpact", ""))).lower() for token in ("khoa học", "công nghệ", "lập trình", "kinh doanh")) else 1.0
    return _clamp((role_score + scale_score) * multiplier)


def calculate_matches(profile: dict[str, Any]) -> dict[str, Any]:
    results = []
    for industry in INDUSTRIES:
        scores = {"S1": _s1(profile, industry), "S2": _s2(profile), "S3": _s3(profile, industry), "S4": _s4(profile, industry), "S5": _s5(profile)}
        weights = {criterion: ROC_WEIGHTS[index] for index, criterion in enumerate(industry.priority)}
        match_score = sum(scores[key] * weights[key] for key in scores)
        results.append({
            "code": industry.code,
            "name": industry.name,
            "score": round(match_score * 10, 2),
            "scores": {key: round(value, 2) for key, value in scores.items()},
            "highlight": max(scores, key=scores.get),
            "subjects": list(industry.subjects),
            "riasec": list(industry.riasec),
        })
    results.sort(key=lambda item: (-item["score"], item["code"]))
    for index, item in enumerate(results, 1):
        item["rank"] = index
    return {"results": results, "top5": results[:5], "top3": results[:3], "riasec": _riasec_scores(profile)}
