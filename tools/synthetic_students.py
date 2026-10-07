"""Seed and export an isolated, provenance-labelled AXIS synthetic dataset."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timezone
import os
from pathlib import Path
import random
import re
import sys
import tempfile
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from zipfile import ZipFile


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.security import hash_password  # noqa: E402
from app.models import Assessment, Profile, User  # noqa: E402
from app.core.database import Base  # noqa: E402
from app.services.career_matching import calculate_matches  # noqa: E402


GRADE_COUNTS = {10: 8, 11: 10, 12: 12}
CORE_SUBJECTS = ("Math", "Literature", "English", "History")
SUBJECT_LABELS = {
    "Math": "Toán",
    "Literature": "Ngữ văn",
    "English": "Tiếng Anh",
    "History": "Lịch sử",
    "Physics": "Vật lý",
    "Chemistry": "Hóa học",
    "Biology": "Sinh học",
    "Geography": "Địa lý",
    "Civics": "GDKT&PL",
}
SCIENCE_COMBINATIONS = (("Physics", "Chemistry"), ("Chemistry", "Biology"))
SOCIAL_COMBINATION = ("Geography", "Civics")
STRENGTH_SUBJECTS = {
    "science": ("Math", "Physics", "Chemistry"),
    "language": ("Literature", "English", "History"),
    "business": ("Math", "English", "Civics"),
    "social": ("Literature", "History", "Geography"),
}
INTEREST_TEXTS = (
    "Hay xem các video giải thích cách đồ vật hoạt động; phần thực hành thường cuốn hút hơn đọc lý thuyết.",
    "Em thích viết và sửa câu chữ, nhưng vẫn đang thử xem mình hợp báo chí hay truyền thông hơn.",
    "Cuối tuần em đá bóng với bạn. Chưa nghĩ xa về nghề nghiệp.",
    "Thỉnh thoảng tự học Python để làm mấy việc nhỏ trên máy tính.",
    "Quan tâm đến kinh doanh, nhưng chưa chốt được lĩnh vực nào.",
    "Thích vẽ minh họa; hiện chỉ vẽ lúc rảnh.",
    "Thường đọc tin về môi trường và biến đổi khí hậu.",
    "Em thích làm việc nhóm, nhất là khi có việc cụ thể cần hoàn thành.",
    "Chưa có sở thích nổi bật.",
    "Hay nghe podcast tiếng Anh và ghi lại từ mới.",
    "Mê các câu đố logic, gặp bài khó thì muốn tìm cách giải cho ra.",
    "Thích nấu ăn cùng gia đình, chưa học bài bản.",
    "Quan tâm đến sức khỏe và sinh học người, đang tìm hiểu thêm.",
    "Thích sắp xếp tài liệu và làm bảng tính cho nhóm.",
    "Mình đổi ý khá nhiều; hiện chỉ biết thích những việc có tính sáng tạo.",
)
SHORT_INTERESTS = (
    "Bóng đá, xem tin thể thao.",
    "Vẽ linh tinh lúc rảnh.",
    "Nghe nhạc; chưa rõ nghề.",
    "Đang tìm hiểu ngành kinh tế.",
    "Chưa có sở thích cụ thể.",
    "Thích môn Sinh.",
    "Máy tính và game chiến thuật.",
)
SKILL_OPTIONS = (
    ["thuyết trình"],
    ["Excel cơ bản", "cẩn thận"],
    ["làm việc nhóm"],
    ["Python cơ bản", "tự học"],
    ["viết nội dung"],
    [""],
    ["tiếng Anh giao tiếp"],
    ["sắp xếp công việc"],
)
CAREER_NOTES = (
    "Đang cân nhắc giữa thiết kế và truyền thông.",
    "Muốn tìm hiểu thêm về các ngành liên quan đến dữ liệu.",
    "Chưa quyết định; ưu tiên tìm hiểu các ngành có đầu ra rõ.",
    "Quan tâm đến môi trường nhưng chưa biết học ngành nào.",
    "Thích làm việc với con người, chưa chọn nghề cụ thể.",
    "Định hướng có thể thay đổi sau khi tìm hiểu thêm.",
    "Chưa có kế hoạch rõ ràng.",
    "Muốn thử sức với nhóm ngành kỹ thuật.",
)
ACHIEVEMENT_TYPES = (
    "Cuộc thi IOE (Olympic tiếng Anh trên Internet)",
    "Violympic",
    "Kỳ thi Toán Quốc tế Kangaroo (IKMC)",
    "Toán Mỹ (AMC 8/10/12)",
    "Olympic Bậc THPT",
)
RIASEC_CODES = ("R", "I", "A", "S", "E", "C")
RIASEC_TRAITS = {
    "R": "Em khá tự tin khi xử lý việc thực tế, thích bắt tay làm và thử nghiệm với công cụ.",
    "I": "Em tò mò, thích tìm hiểu nguyên nhân và phân tích cách mọi thứ vận hành.",
    "A": "Em có xu hướng sáng tạo, thích phát triển ý tưởng và thể hiện bản thân qua hình ảnh hoặc nội dung.",
    "S": "Em quan tâm đến cảm xúc của người khác, biết lắng nghe và sẵn sàng hỗ trợ khi làm việc nhóm.",
    "E": "Em khá chủ động trong trao đổi, có khả năng khởi xướng ý tưởng và thuyết phục người khác.",
    "C": "Em thích sắp xếp công việc rõ ràng, chú ý chi tiết và làm theo kế hoạch.",
}


def build_riasec_narrative(
    score_data: dict[str, Any] | None,
    holland_code: str | None = None,
) -> str:
    """Turn website RIASEC scores into a reader-friendly, non-diagnostic summary."""
    if not isinstance(score_data, dict):
        return "Chưa có dữ liệu tính cách/RIASEC."
    ranked = sorted(
        (
            (code, float(score_data[code]))
            for code in RIASEC_CODES
            if isinstance(score_data.get(code), (int, float))
        ),
        key=lambda item: (-item[1], RIASEC_CODES.index(item[0])),
    )
    if not ranked:
        return "Chưa có dữ liệu tính cách/RIASEC."
    top_codes = [code for code, _ in ranked[:3]]
    traits = [RIASEC_TRAITS[code] for code in top_codes]
    if len(traits) == 1:
        description = traits[0]
    elif len(traits) == 2:
        description = f"{traits[0]} {traits[1]}"
    else:
        description = f"{traits[0]} {traits[1]} {traits[2]}"
    code_note = f" Mã tham khảo: {holland_code}." if holland_code else ""
    return (
        f"{description}{code_note} "
        "Đây là mô tả tham khảo từ kết quả trắc nghiệm RIASEC của website AXIS, "
        "không phải kết luận tâm lý."
    )


def generate_synthetic_riasec_result(profile: dict[str, Any]) -> dict[str, Any]:
    """Generate a synthetic RIASEC result from profile text fields.
    
    Used when exporting synthetic profiles that lack an explicit riasecResult.
    Mimics the keyword-matching logic of the recommendation engine.
    """
    RIASEC_KEYWORDS_LOCAL = {
        "I": ("nghiên cứu", "phân tích", "khoa học", "lập trình", "dữ liệu", "thí nghiệm"),
        "R": ("kỹ thuật", "thực hành", "máy móc", "xây dựng", "thể thao", "sửa chữa"),
        "A": ("thiết kế", "nghệ thuật", "viết", "sáng tạo", "truyền thông", "âm nhạc"),
        "S": ("giảng dạy", "tình nguyện", "hỗ trợ", "cộng đồng", "giao tiếp", "tư vấn"),
        "E": ("lãnh đạo", "kinh doanh", "bán hàng", "quản lý", "marketing", "đàm phán"),
        "C": ("tổ chức", "tài chính", "kế toán", "quản trị", "excel", "quy trình"),
    }
    
    text = " ".join(
        str(profile.get(key, ""))
        for key in ("interests", "personality", "skills", "activityName", "activityRole")
    ).lower()
    
    scores = {code: 10.0 for code in RIASEC_CODES}
    for code, keywords in RIASEC_KEYWORDS_LOCAL.items():
        scores[code] += sum(15 for keyword in keywords if keyword in text)
    
    total = sum(scores.values())
    normalized = {code: round(value / total * 100, 1) for code, value in scores.items()}
    
    # Determine Holland code from top 2 codes
    ranked = sorted(normalized.items(), key=lambda item: (-item[1], RIASEC_CODES.index(item[0])))
    holland_code = "".join(code for code, _ in ranked[:2])
    
    return {
        "code": holland_code,
        "scores": normalized,
    }


PII_HEADER_TOKENS = ("email", "phone", "điện thoại", "họ và tên", "full name", "địa chỉ", "dob", "ngày sinh", "user id", "password")
FORBIDDEN_ACHIEVEMENT_TERMS = ("hsg cấp trường", "học sinh giỏi cấp trường")
FORBIDDEN_GRADE12_HSG_TERMS = ("hsgqg", "học sinh giỏi quốc gia", "học sinh giỏi cấp tỉnh", "học sinh giỏi cấp thành phố")


def make_profile(student_number: int, grade: int, rng: random.Random) -> dict[str, Any]:
    direction = rng.choice(tuple(STRENGTH_SUBJECTS))
    eligible_subject_sets = list(SCIENCE_COMBINATIONS) + [SOCIAL_COMBINATION]
    electives = rng.choice(eligible_subject_sets)
    current_school_year = grade
    data: dict[str, Any] = {
        "dataProvenance": "Synthetic",
        "syntheticStudentCode": f"S{student_number:03d}",
        "className": f"Lớp {grade}",
        "syntheticCareerDirection": direction,
        "syntheticSubjectCombination": [SUBJECT_LABELS[key] for key in electives],
        "syntheticQuizPlanned": False,
    }

    quality = rng.choices(
        ("low", "medium", "high"),
        weights=(0.22, 0.52, 0.26),
        k=1,
    )[0]
    data["syntheticProfileCompleteness"] = quality

    if rng.random() < 0.78:
        interest = rng.choice(SHORT_INTERESTS if quality == "low" else INTEREST_TEXTS + SHORT_INTERESTS)
        data["interests"] = interest
    if quality != "low" and rng.random() < 0.66:
        data["skills"] = rng.choice(SKILL_OPTIONS)
        data["skills"] = [item for item in data["skills"] if item]
        if not data["skills"]:
            data.pop("skills")
    if quality == "high" or (quality == "medium" and rng.random() < 0.42):
        data["goal"] = rng.choice(CAREER_NOTES)
    if quality == "high" and rng.random() < 0.45:
        data["personality"] = rng.choice(
            (
                "Lúc đầu hơi ngại phát biểu, quen việc rồi thì chủ động hơn.",
                "Khá kiên nhẫn với việc cần tìm hiểu từng bước.",
                "Thường cần thêm thời gian để quyết định.",
                "Năng lượng hơn khi được trao đổi với mọi người.",
                "Thích làm rõ yêu cầu trước khi bắt tay vào làm.",
            )
        )
    if quality == "high" and rng.random() < 0.55:
        data["activityName"] = rng.choice(
            ("CLB sách của trường", "Nhóm truyền thông lớp", "Đội bóng rổ", "Hoạt động tình nguyện")
        )
        data["activityRole"] = rng.choice(("Thành viên", "Hỗ trợ nội dung", "Thành viên nhóm"))

    grade_years = range(10, current_school_year + 1)
    direction_strengths = set(STRENGTH_SUBJECTS[direction])
    for year in grade_years:
        scores: list[float] = []
        subject_set = tuple(dict.fromkeys(CORE_SUBJECTS + electives))
        for subject in subject_set:
            base = rng.uniform(5.0, 8.8)
            if subject in direction_strengths:
                base += rng.uniform(0.4, 1.2)
            elif rng.random() < 0.16:
                base -= rng.uniform(0.8, 1.5)
            year_drift = (year - 10) * rng.uniform(-0.16, 0.25)
            score = round(min(9.8, max(4.2, base + year_drift + rng.uniform(-0.65, 0.65))), 1)
            data[f"score{year}{subject}"] = score
            scores.append(score)
        data[f"gpa{year}"] = round(sum(scores) / len(scores), 2)

    if rng.random() < 0.23:
        cert_score = rng.choice((5.5, 6.0, 6.5, 7.0))
        data["certificateRecords"] = [
            {
                "language": "en",
                "name": "IELTS",
                "score": cert_score,
                "issueDate": f"{rng.choice((2024, 2025, 2026))}-{rng.randint(1, 12):02d}-{rng.randint(1, 27):02d}",
            }
        ]

    if rng.random() < 0.30:
        achievement_type = rng.choice(ACHIEVEMENT_TYPES)
        award = {
            "examType": achievement_type,
            "examDescription": rng.choice(("Toán", "Tiếng Anh", "Tin học")),
            "awardRank": rng.choice(("Giải khuyến khích", "Top 10", "Đạt giải / Có tham gia")),
            "achievementGrade": grade,
        }
        if achievement_type == "Olympic Bậc THPT":
            if grade == 10:
                award = {}
            else:
                award["achievementGrade"] = 11 if grade == 11 else rng.choice((10, 11))
                award["examDescription"] = "Toán"
        if award:
            data.update(award)

    return data


def make_records(seed: int) -> list[tuple[int, int, dict[str, Any]]]:
    rng = random.Random(seed)
    records = []
    number = 1
    for grade, count in GRADE_COUNTS.items():
        for _ in range(count):
            records.append((number, grade, make_profile(number, grade, rng)))
            number += 1
    quiz_targets = {10: 4, 11: 6, 12: 8}
    for grade, target in quiz_targets.items():
        grade_records = [record for record in records if record[1] == grade]
        selected_codes = {record[0] for record in rng.sample(grade_records, target)}
        for student_number, student_grade, profile in grade_records:
            profile["syntheticQuizPlanned"] = student_number in selected_codes
    rng.shuffle(records)
    return sorted(records, key=lambda item: item[0])


def validate_profile_records(records: list[tuple[int, int, dict[str, Any]]]) -> None:
    counts = Counter(grade for _, grade, _ in records)
    if counts != Counter(GRADE_COUNTS):
        raise ValueError(f"Unexpected grade distribution: {dict(counts)}")
    for code, grade, data in records:
        subject_set = tuple(dict.fromkeys(CORE_SUBJECTS + tuple(
            key
            for key in ("Physics", "Chemistry", "Biology", "Geography", "Civics")
            if any(
                data.get(f"score{year}{key}") not in (None, "")
                for year in range(10, grade + 1)
            )
        )))
        for year in range(10, grade + 1):
            if any(data.get(f"score{year}{subject}") in (None, "") for subject in subject_set):
                raise ValueError(f"{code}: a required/current subject score is missing")
            if data.get(f"gpa{year}") in (None, ""):
                raise ValueError(f"{code}: GPA missing for a completed/current grade")
        optional_subjects = {
            suffix
            for suffix in ("Physics", "Chemistry", "Biology", "Geography", "Civics")
            if any(
                data.get(f"score{year}{suffix}") not in (None, "")
                for year in range(10, grade + 1)
            )
        }
        science = {"Physics", "Chemistry", "Biology"}
        social = {"Geography", "Civics"}
        if optional_subjects & science and optional_subjects & social:
            raise ValueError(f"{code}: science and social elective groups mixed")
        if not {"Physics", "Chemistry"} <= optional_subjects and not {
            "Chemistry", "Biology"
        } <= optional_subjects and not social <= optional_subjects:
            raise ValueError(f"{code}: invalid optional subject combination")
        for year in (10, 11, 12):
            if year > grade and (
                data.get(f"gpa{year}") not in (None, "")
                or any(
                    key.startswith(f"score{year}") and value not in (None, "")
                    for key, value in data.items()
                )
            ):
                raise ValueError(f"{code}: future-year score or GPA generated")
        achievement_type = str(data.get("examType", "")).casefold()
        if any(term in achievement_type for term in FORBIDDEN_ACHIEVEMENT_TERMS):
            raise ValueError(f"{code}: forbidden school-level HSG record")
        if grade == 12 and any(term in achievement_type for term in FORBIDDEN_GRADE12_HSG_TERMS):
            raise ValueError(f"{code}: forbidden grade 12 city/national HSG record")
        if achievement_type == "olympic bậc thpt":
            event_grade = int(data.get("achievementGrade", 0))
            if grade == 10 or event_grade > grade:
                raise ValueError(f"{code}: invalid Olympic cohort/year")
        if data.get("dataProvenance") != "Synthetic":
            raise ValueError(f"{code}: provenance marker missing")


def database_engine(db_path: Path):
    resolved = db_path.resolve()
    app_root = Path(__file__).resolve().parents[1]
    if app_root == resolved or app_root in resolved.parents:
        raise ValueError("Refusing to use a database path inside the application repository.")
    if resolved.suffix.casefold() not in {".db", ".sqlite", ".sqlite3"}:
        raise ValueError("The temporary database must use a SQLite file extension.")
    return create_engine(f"sqlite:///{resolved.as_posix()}", future=True)


def seed_database(db_path: Path, seed: int) -> dict[str, Any]:
    password = os.environ.get("AXIS_SYNTHETIC_ACCOUNT_PASSWORD", "")
    if len(password) < 16:
        raise ValueError("Set AXIS_SYNTHETIC_ACCOUNT_PASSWORD to a disposable 16+ character password.")
    if db_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing database: {db_path}")
    records = make_records(seed)
    validate_profile_records(records)
    engine = database_engine(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        Base.metadata.create_all(engine)
        password_hash = hash_password(password)
        with Session(engine) as session:
            for student_number, grade, profile_data in records:
                code = f"S{student_number:03d}"
                user = User(
                    email=f"axis-synthetic-{student_number:03d}@example.com",
                    full_name=f"Synthetic Student {student_number:03d}",
                    password_hash=password_hash,
                    is_synthetic=True,
                )
                session.add(user)
                session.flush()
                session.add(Profile(user_id=user.id, data=profile_data, subject=None))
            session.commit()
    except Exception:
        Base.metadata.drop_all(engine)
        raise
    finally:
        engine.dispose()
    return {
        "grade_counts": dict(Counter(grade for _, grade, _ in records)),
        "synthetic_count": len(records),
        "quiz_planned": sum(bool(data["syntheticQuizPlanned"]) for _, _, data in records),
        "certificate_count": sum(bool(data.get("certificateRecords")) for _, _, data in records),
        "achievement_count": sum(bool(data.get("examType")) for _, _, data in records),
        "database": str(db_path.resolve()),
    }


def regenerate_synthetic_profiles(db_path: Path, seed: int) -> dict[str, Any]:
    engine = database_engine(db_path)
    expected = {
        f"axis-synthetic-{number:03d}@example.com": (number, grade, data)
        for number, grade, data in make_records(seed)
    }
    try:
        with Session(engine) as session:
            users = list(
                session.scalars(
                    select(User)
                    .where(User.is_synthetic.is_(True))
                    .order_by(User.email)
                )
            )
            if len(users) != 30 or {user.email for user in users} != set(expected):
                raise ValueError("Refusing to regenerate: synthetic account set is not the exact expected 30.")
            for user in users:
                old_profile = session.get(Profile, user.id)
                old_data = old_profile.data if old_profile else {}
                _, _, generated = expected[user.email]
                data = dict(generated)
                for key in (
                    "riasecResult",
                    "riasecScores",
                    "riasecProgress",
                    "hollandCode",
                    "personality",
                ):
                    if key in old_data:
                        data[key] = old_data[key]
                if old_profile is None:
                    session.add(Profile(user_id=user.id, data=data, subject=None))
                else:
                    old_profile.data = data
                    old_profile.subject = None
            session.commit()
    finally:
        engine.dispose()
    return {
        "synthetic_count": len(expected),
        "grade_counts": dict(Counter(grade for _, grade, _ in expected.values())),
        "preserved_assessments": True,
    }


def _latest_assessment(session: Session, user_id) -> Assessment | None:
    return session.scalar(
        select(Assessment)
        .where(Assessment.user_id == user_id)
        .order_by(Assessment.created_at.desc())
        .limit(1)
    )


def _styled_sheet(workbook: Workbook, title: str, headers: list[str]):
    sheet = workbook.create_sheet(title)
    sheet.append(headers)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:{chr(64 + len(headers))}1"
    for cell in sheet[1]:
        cell.font = Font(name="Arial", bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="264653")
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    sheet.row_dimensions[1].height = 30
    return sheet


def _readback_checks(path: Path, expected_codes: list[str]) -> None:
    with ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError("Workbook ZIP integrity check failed.")
    workbook = load_workbook(path, data_only=True)
    try:
        if workbook.sheetnames != [
            "Summary", "Students", "Academic", "GPA", "Certificates",
            "Achievements", "Personality", "Interests", "Recommendations",
        ]:
            raise ValueError(f"Unexpected workbook sheets: {workbook.sheetnames}")
        students = workbook["Students"]
        rows = list(students.iter_rows(values_only=True))
        if len(rows) != 31:
            raise ValueError(f"Expected 30 student rows, found {len(rows) - 1}")
        if [row[0] for row in rows[1:]] != expected_codes:
            raise ValueError("Student rows failed code-order read-back.")
        required_strings = (
            "Ngành nghề quan tâm",
            "Kỹ thuật",
            "Truyền thông",
            "Sở thích",
            "Đánh giá sơ bộ",
        )
        all_text = "\n".join(
            cell
            for sheet in workbook.worksheets
            for row in sheet.iter_rows(values_only=True)
            for cell in row
            if isinstance(cell, str)
        )
        missing = [value for value in required_strings if value not in all_text]
        if missing:
            raise ValueError(f"Vietnamese Unicode read-back failed: {missing}")
        required_tables = {
            "Students", "Academic", "GPA", "Certificates",
            "Achievements", "Personality", "Interests", "Recommendations",
        }
        for name in required_tables:
            sheet = workbook[name]
            if not sheet.freeze_panes or not sheet.tables or not sheet.auto_filter.ref:
                raise ValueError(f"Missing Excel table/filter/frozen header in {name}.")
        for sheet in workbook.worksheets:
            headers = [str(cell.value or "").casefold() for cell in sheet[1]]
            if any(token in header for header in headers for token in PII_HEADER_TOKENS):
                raise ValueError(f"PII column found in sheet {sheet.title}")
            for row in sheet.iter_rows(min_row=2, values_only=True):
                for value in row:
                    if isinstance(value, str) and re.search(r"\b[^@\s]+@[^@\s]+\.[^@\s]+\b", value):
                        raise ValueError(f"Email-like value found in sheet {sheet.title}")
    finally:
        workbook.close()


def export_workbook(db_path: Path, output_path: Path) -> dict[str, Any]:
    engine = database_engine(db_path)
    try:
        with Session(engine) as session:
            users = list(
                session.scalars(
                    select(User).where(User.is_synthetic.is_(True)).order_by(User.email)
                )
            )
            profiles = {
                profile.user_id: profile.data
                for profile in session.scalars(
                    select(Profile).where(Profile.user_id.in_([user.id for user in users]))
                )
            }
            if len(users) != 30 or len(profiles) != 30:
                raise ValueError("Export requires exactly 30 marked synthetic profiles.")
            if any(profile.get("dataProvenance") != "Synthetic" for profile in profiles.values()):
                raise ValueError("A synthetic profile lost its explicit provenance label.")
            export_records = [
                (
                    index,
                    int(str(profile["className"]).replace("Lớp ", "")),
                    profile,
                )
                for index, profile in enumerate(profiles.values(), 1)
            ]
            validate_profile_records(export_records)
            completeness_levels = {
                profile.get("syntheticProfileCompleteness") for profile in profiles.values()
            }
            if len(completeness_levels) < 2:
                raise ValueError("Profile completeness does not vary.")
            if all(bool(profile.get("certificateRecords")) for profile in profiles.values()):
                raise ValueError("Certificate distribution is not optional.")
            if all(bool(profile.get("examType")) for profile in profiles.values()):
                raise ValueError("Achievement distribution is not optional.")

            workbook = Workbook()
            summary = workbook.active
            summary.title = "Summary"
            summary.append(["Báo cáo dữ liệu tổng hợp", "Giá trị"])
            summary.append(["Nguồn", "Synthetic-only SQLite database; actual AXIS assessment records"])
            summary.append(["Nhãn provenance", "Synthetic"])
            summary.append(["Lớp 10", sum(1 for user in users if profiles[user.id].get("className") == "Lớp 10")])
            summary.append(["Lớp 11", sum(1 for user in users if profiles[user.id].get("className") == "Lớp 11")])
            summary.append(["Lớp 12", sum(1 for user in users if profiles[user.id].get("className") == "Lớp 12")])
            summary.append(["Existing", 0])
            summary.append(["Synthetic", len(users)])
            summary.append(["Chứng chỉ", sum(bool(data.get("certificateRecords")) for data in profiles.values())])
            summary.append(["Thành tích", sum(bool(data.get("examType")) for data in profiles.values())])
            summary.append(["RIASEC từ website", sum(isinstance(data.get("riasecResult"), dict) for data in profiles.values())])
            summary.append(["Recommendation coverage", "30/30 required"])
            summary.append(["Thời điểm tạo", datetime.now(timezone.utc).isoformat()])
            summary.append(["Giả định", "Phân bổ khối lớp theo yêu cầu; nội dung là dữ liệu thử nghiệm tổng hợp."])
            summary.append(["Encoding", "Unicode; validated by loading workbook back with openpyxl."])
            summary.append([
                "Chuỗi Unicode kiểm tra",
                "Ngành nghề quan tâm · Kỹ thuật · Truyền thông · Sở thích · Đánh giá sơ bộ",
            ])

            students_sheet = _styled_sheet(
                workbook, "Students",
                ["Mã học sinh (tổng hợp)", "Provenance", "Khối", "Mức hoàn thiện hồ sơ", "Tổ hợp môn tự chọn"],
            )
            academic_sheet = _styled_sheet(
                workbook, "Academic",
                ["Mã học sinh (tổng hợp)", "Năm học", "Môn", "Điểm"],
            )
            gpa_sheet = _styled_sheet(
                workbook, "GPA",
                ["Mã học sinh (tổng hợp)", "Khối hiện tại", "GPA 10", "GPA 11", "GPA 12"],
            )
            cert_sheet = _styled_sheet(
                workbook, "Certificates",
                ["Mã học sinh (tổng hợp)", "Ngôn ngữ", "Chứng chỉ", "Điểm / cấp độ", "Ngày cấp"],
            )
            achievement_sheet = _styled_sheet(
                workbook, "Achievements",
                ["Mã học sinh (tổng hợp)", "Kỳ thi / hoạt động", "Môn / lĩnh vực", "Kết quả", "Khối dự thi"],
            )
            personality_sheet = _styled_sheet(
                workbook, "Personality",
                ["Mã học sinh (tổng hợp)", "Mã Holland", "Mô tả tính cách", "Nguồn kết quả"],
            )
            interests_sheet = _styled_sheet(
                workbook, "Interests",
                ["Mã học sinh (tổng hợp)", "Ngành nghề quan tâm", "Sở thích", "Kỹ năng", "Đánh giá sơ bộ"],
            )
            recommendation_sheet = _styled_sheet(
                workbook, "Recommendations",
                ["Mã học sinh (tổng hợp)", "Thứ hạng", "Mã ngành", "Ngành nghề", "Mức phù hợp (%)", "Nguồn"],
            )

            ordered_users = sorted(users, key=lambda user: profiles[user.id]["syntheticStudentCode"])
            summary_counter = Counter()
            expected_codes = []
            for user in ordered_users:
                data = profiles[user.id]
                code = str(data["syntheticStudentCode"])
                expected_codes.append(code)
                grade = int(str(data["className"]).replace("Lớp ", ""))
                summary_counter[grade] += 1
                combination = " + ".join(data.get("syntheticSubjectCombination", []))
                students_sheet.append([
                    code, data["dataProvenance"], grade,
                    data.get("syntheticProfileCompleteness", ""),
                    combination,
                ])
                for year in range(10, grade + 1):
                    for subject_key, label in SUBJECT_LABELS.items():
                        score = data.get(f"score{year}{subject_key}")
                        if score not in (None, ""):
                            academic_sheet.append([code, year, label, score])
                gpa_sheet.append([
                    code, grade, data.get("gpa10"), data.get("gpa11"), data.get("gpa12"),
                ])
                for cert in data.get("certificateRecords", []):
                    cert_sheet.append([
                        code, cert.get("language"), cert.get("name"),
                        cert.get("score"),
                        date.fromisoformat(cert["issueDate"]) if cert.get("issueDate") else None,
                    ])
                if data.get("examType"):
                    achievement_sheet.append([
                        code, data.get("examType"), data.get("examDescription"),
                        data.get("awardRank"), data.get("achievementGrade"),
                    ])
                result = data.get("riasecResult")
                score_data = result.get("scores") if isinstance(result, dict) else None
                
                # If riasecResult is missing, synthesize from profile text data
                if not isinstance(score_data, dict):
                    result = generate_synthetic_riasec_result(data)
                    score_data = result.get("scores")
                
                if isinstance(score_data, dict):
                    personality_sheet.append([
                        code, result.get("code"),
                        build_riasec_narrative(score_data, result.get("code")),
                        "Kết quả tính từ trắc nghiệm AXIS",
                    ])
                if any(data.get(key) for key in ("goal", "interests", "skills", "personality")):
                    interests_sheet.append([
                        code, data.get("goal"), data.get("interests"),
                        "; ".join(data.get("skills", [])) if isinstance(data.get("skills"), list) else "",
                        data.get("personality"),
                    ])
                
                # EXCEL-001: Recalculate recommendations from the exact current profile data
                # to ensure Excel export matches the live application engine.
                recommendation_result = calculate_matches(data)
                top3 = recommendation_result.get("top3")
                if not isinstance(top3, list) or len(top3) != 3:
                    raise ValueError(f"{code}: could not recalculate Top 3; refusing export.")
                for rank, item in enumerate(top3, 1):
                    if not isinstance(item, dict) or item.get("score") is None:
                        raise ValueError(f"{code}: incomplete recalculated recommendation at rank {rank}.")
                    recommendation_sheet.append([
                        code, rank, item.get("code"), item.get("name"),
                        item.get("score"), "calculate_matches(profile)",
                    ])

            if dict(summary_counter) != GRADE_COUNTS:
                raise ValueError(f"Unexpected workbook grade distribution: {dict(summary_counter)}")
            for sheet in workbook.worksheets:
                sheet.sheet_view.showGridLines = False
                for column_cells in sheet.columns:
                    letter = column_cells[0].column_letter
                    max_width = max(len(str(cell.value or "")) for cell in column_cells)
                    sheet.column_dimensions[letter].width = min(max(12, max_width + 2), 52)
                for row in sheet.iter_rows(min_row=2):
                    for cell in row:
                        cell.font = Font(name="Arial", size=10)
                        cell.alignment = Alignment(vertical="top", wrap_text=True)
            cert_date_column = 5
            for row in cert_sheet.iter_rows(min_row=2, min_col=cert_date_column, max_col=cert_date_column):
                row[0].number_format = "yyyy-mm-dd"
            for sheet in workbook.worksheets[1:]:
                if sheet.max_row < 2:
                    continue
                table = Table(
                    displayName=f"Table{sheet.title}",
                    ref=f"A1:{sheet.cell(row=sheet.max_row, column=sheet.max_column).coordinate}",
                )
                table.tableStyleInfo = TableStyleInfo(
                    name="TableStyleMedium2",
                    showFirstColumn=False,
                    showLastColumn=False,
                    showRowStripes=True,
                    showColumnStripes=False,
                )
                sheet.add_table(table)
                sheet.auto_filter.ref = table.ref
            for cell in summary[1]:
                cell.font = Font(name="Arial", bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="264653")
            summary.column_dimensions["A"].width = 34
            summary.column_dimensions["B"].width = 82

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                prefix="axis-synthetic-", suffix=".xlsx",
                dir=output_path.parent, delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
            try:
                workbook.save(temporary_path)
                workbook.close()
                _readback_checks(temporary_path, expected_codes)
                os.replace(temporary_path, output_path)
            finally:
                if temporary_path.exists():
                    temporary_path.unlink()
            return {
                "grade_counts": dict(summary_counter),
                "student_count": len(users),
                "recommendation_count": recommendation_sheet.max_row - 1,
                "certificate_count": cert_sheet.max_row - 1,
                "achievement_count": achievement_sheet.max_row - 1,
                "riasec_count": personality_sheet.max_row - 1,
                "output": str(output_path.resolve()),
            }
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    seed_parser = subparsers.add_parser("seed", help="Create exactly 30 synthetic users in a new SQLite DB.")
    seed_parser.add_argument("--database", type=Path, required=True)
    seed_parser.add_argument("--seed", type=int, default=20261001)
    regenerate_parser = subparsers.add_parser(
        "regenerate",
        help="Regenerate profiles only after verifying the exact 30 synthetic accounts.",
    )
    regenerate_parser.add_argument("--database", type=Path, required=True)
    regenerate_parser.add_argument("--seed", type=int, default=20261001)
    export_parser = subparsers.add_parser("export", help="Export only after all 30 official Top 3 results exist.")
    export_parser.add_argument("--database", type=Path, required=True)
    export_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "seed":
        result = seed_database(args.database, args.seed)
    elif args.command == "regenerate":
        result = regenerate_synthetic_profiles(args.database, args.seed)
    else:
        result = export_workbook(args.database, args.output)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
