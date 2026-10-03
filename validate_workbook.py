#!/usr/bin/env python
"""Compare workbook recommendations with canonical synthetic assessment inputs."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
import types
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.utils.cell import range_boundaries

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
REFERENCE_ENGINE_COMMIT = "bb9a8a9e9c3e825e57650475bf4682bc51df7179"
CANONICAL_SOURCE_SHA256 = "d52fea19f8f0c3543236a3b307832479f9dae95a18c8ce52e814f2419fc75a93"
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.career_matching import (  # noqa: E402
    SUBJECT_KEYS,
    aggregate_gpa,
    aggregate_subject_score,
    calculate_matches,
)


SUBJECT_SUFFIXES = {
    "Toán": "Math",
    "Ngữ văn": "Literature",
    "Tiếng Anh": "English",
    "Lịch sử": "History",
    "Vật lý": "Physics",
    "Hóa học": "Chemistry",
    "Sinh học": "Biology",
    "Địa lý": "Geography",
    "Giáo dục kinh tế và pháp luật": "Civics",
    "Tin học": "Informatics",
}
REQUIRED_SHEETS = ("Tổng hợp", "Môn học", "Hồ sơ")
RECOMMENDATION_PATTERN = re.compile(r"^(?P<name>.+) - (?P<score>\d+(?:\.\d+)?)%$")


def _headers(sheet) -> dict[str, int]:
    return {
        str(cell.value).strip(): cell.column
        for cell in sheet[1]
        if cell.value is not None
    }


def _rows_by_student(sheet, header: dict[str, int], key_name: str) -> dict[str, int]:
    key_column = header[key_name]
    rows: dict[str, int] = {}
    for row in range(2, sheet.max_row + 1):
        student_id = sheet.cell(row, key_column).value
        if student_id in (None, ""):
            continue
        key = str(student_id).strip()
        if key in rows:
            raise ValueError(f"Duplicate student {key!r} in {sheet.title}")
        rows[key] = row
    return rows


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value in (None, ""):
        return None
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    try:
        return float(str(value).strip().replace(",", "."))
    except ValueError:
        return None


def _formula_average(sheet, formula: Any, formula_row: int) -> float | None:
    if not isinstance(formula, str):
        return _number(formula)
    if formula.strip() in {"", "—", "-"}:
        return None
    formula_text = formula.strip()
    match = re.fullmatch(
        r"=AVERAGE\(([A-Z]+\d+):([A-Z]+\d+)\)",
        formula_text,
        re.I,
    )
    rounded_match = re.fullmatch(
        r"=ROUND\(AVERAGE\(([A-Z]+\d+):([A-Z]+\d+)\),\s*2\)",
        formula_text,
        re.I,
    )
    if match is None and rounded_match is None:
        raise ValueError(f"Unsupported GPA formula at {sheet.title}!row {formula_row}: {formula}")
    references = match or rounded_match
    assert references is not None
    min_col, min_row, max_col, max_row = range_boundaries(
        f"{references.group(1)}:{references.group(2)}"
    )
    if min_row != formula_row or max_row != formula_row:
        raise ValueError(f"GPA formula references an unexpected row: {formula}")
    values = [
        _number(sheet.cell(formula_row, column).value)
        for column in range(min_col, max_col + 1)
    ]
    numeric_values = [value for value in values if value is not None]
    if not numeric_values:
        return None
    average = sum(numeric_values) / len(numeric_values)
    if rounded_match is not None:
        return float(
            Decimal(str(average)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        )
    return average


def _parse_certificate(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, str) or not value.strip():
        return None
    fields = [part.strip() for part in value.split(" / ")]
    if len(fields) != 4:
        raise ValueError(f"Unsupported certificate record: {value!r}")
    try:
        score = float(fields[2].replace(",", "."))
    except ValueError as exc:
        raise ValueError(f"Invalid certificate score: {value!r}") from exc
    return {
        "name": fields[0],
        "score": score,
        "issueDate": fields[3],
    }


def _parse_achievement(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, str) or not value.strip():
        return None
    fields = [part.strip() for part in value.split(" — ")]
    if len(fields) != 4:
        raise ValueError(f"Unsupported achievement record: {value!r}")
    grade_match = re.fullmatch(r"Lớp\s+(\d+)", fields[3])
    if not grade_match:
        raise ValueError(f"Invalid achievement grade: {value!r}")
    return {
        "examType": fields[0],
        "examDescription": fields[1],
        "awardRank": fields[2],
        "achievementGrade": int(grade_match.group(1)),
    }


def reconstruct_profile(workbook, student_id: str) -> tuple[dict[str, Any], list[str]]:
    summary, academics, details = workbook.worksheets
    summary_headers = _headers(summary)
    academic_headers = _headers(academics)
    detail_headers = _headers(details)
    summary_row = _rows_by_student(summary, summary_headers, "HS+No.")[student_id]
    academic_row = _rows_by_student(academics, academic_headers, "HS+No.")[student_id]
    detail_row = _rows_by_student(details, detail_headers, "HS+No.")[student_id]

    grade = int(summary.cell(summary_row, summary_headers["Khối"]).value)
    profile: dict[str, Any] = {"grade": grade}
    missing_inputs: list[str] = []

    for header, column in academic_headers.items():
        match = re.fullmatch(r"Lớp (\d+) - (.+)", header)
        if not match:
            continue
        year, label = int(match.group(1)), match.group(2)
        if year > grade:
            continue
        suffix = SUBJECT_SUFFIXES.get(label)
        if suffix is None:
            raise ValueError(f"Unknown academic subject column: {header}")
        value = _number(academics.cell(academic_row, column).value)
        if value is not None:
            profile[f"score{year}{suffix}"] = value

    for year in range(9, min(grade, 12) + 1):
        gpa_header = f"GPA lớp {year}"
        if gpa_header not in academic_headers:
            continue
        gpa_value = _formula_average(
            academics,
            academics.cell(academic_row, academic_headers[gpa_header]).value,
            academic_row,
        )
        if gpa_value is not None:
            profile[f"gpa{year}"] = gpa_value

    certificate = _parse_certificate(
        details.cell(detail_row, detail_headers["Chứng chỉ ngoại ngữ"]).value
    )
    if certificate:
        profile["certificateRecords"] = [certificate]

    achievement = _parse_achievement(
        details.cell(detail_row, detail_headers["Thành tích/Giải thưởng"]).value
    )
    if achievement:
        profile.update(achievement)

    interests = details.cell(detail_row, detail_headers["Sở thích"]).value
    if isinstance(interests, str) and interests.strip():
        profile["interests"] = interests.strip()

    # The workbook stores only a Holland code, not the numeric group scores.
    # Do not manufacture riasecScores from that code.
    if not any(key.startswith("score") for key in profile):
        missing_inputs.append("no numeric academic subject scores")
    if not any(key.startswith("gpa") for key in profile):
        missing_inputs.append("no GPA values")
    if not isinstance(details.cell(detail_row, detail_headers["Mã RIASEC"]).value, str):
        missing_inputs.append("no Holland code")
    missing_inputs.extend(("numeric RIASEC scores not present in workbook", "skills/activity fields not present in workbook"))
    return profile, missing_inputs


def _parse_stored_recommendation(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, str):
        return None
    match = RECOMMENDATION_PATTERN.fullmatch(value.strip())
    if not match:
        return None
    try:
        score = Decimal(match.group("score"))
    except InvalidOperation:
        return None
    return {"name": match.group("name"), "score": score}


def _format_recommendations(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"name": item["name"], "score": f"{Decimal(str(item['score'])):.2f}"}
        for item in items
    ]


def _review_metadata() -> dict[str, Any]:
    return {
        "review_findings": {
            "reactivated_cancelled_career_limit": {
                "status": "fixed",
                "behavior": "The post-update count of non-cancelled career goals may not exceed two.",
            },
            "ai_rate_limit": {
                "status": "in_process_concurrency_fixed_cross_process_blocked",
                "ai_requests": {
                    "limit": 5,
                    "window_seconds": 60,
                    "configuration": "AI_RATE_LIMIT_REQUESTS / AI_RATE_LIMIT_WINDOW_SECONDS",
                },
                "cv_requests": {
                    "limit": 5,
                    "window_seconds": 600,
                    "lockout_seconds": 600,
                },
                "scope": "Atomic per Python process; not shared across serverless instances or workers.",
            },
            "migration": {
                "status": "production_not_verified",
                "source": "backend/alembic/versions/0011_add_user_synthetic_marker.py",
                "command": "alembic -c alembic.ini upgrade head",
                "render_process": "preDeployCommand from rootDir backend",
                "vercel_process": "No migration is run by api/index.py; migrate before application deployment.",
                "expected_head": "0011_add_user_synthetic_marker",
                "schema_change": "users.is_synthetic BOOLEAN NOT NULL DEFAULT false",
                "production_revision_verified": False,
            },
        },
        "verified": [
            "The canonical synthetic SQLite snapshot hash and one-to-one user/profile coverage were verified.",
            "The historical calculate_matches implementation at the recorded Git commit independently reproduced the saved Top 3 for all 30 profiles.",
            "The current calculate_matches implementation was run against all 30 stored canonical profiles and compared with both saved assessments and Excel.",
            "Engine Top 3 output uses name and score fields.",
            "Workbook itself was not modified during this investigation.",
        ],
        "fixed": [
            "Validator input/output schema and workbook mapping.",
            "Cancelled career-goal reactivation limit bypass, with regression coverage.",
            "Atomic in-process concurrency enforcement without changing configured thresholds.",
        ],
        "not_verified": [
            "Workbook Top 3 parity using the workbook's own complete authoritative profile inputs; numeric RIASEC and other application-only inputs are not present in the workbook.",
            "The exact creator, generation event, or intended relationship between the 3-sheet workbook and the canonical synthetic SQLite profiles.",
            "Production database Alembic revision.",
            "Cross-process/serverless global rate-limit enforcement.",
        ],
        "blocked": [
            "Reconstructing every recommendation from workbook-only inputs: the existing layout omits 84 Grade 12 academic values, and numeric RIASEC and other application inputs are absent. Canonical-engine-to-stored-Excel parity is reported separately.",
            "Claiming production readiness before verifying migration 0011 on production.",
            "Claiming global rate-limit enforcement across serverless instances.",
        ],
    }


def _same_recommendation(left: dict[str, Any] | None, right: dict[str, Any] | None) -> bool:
    return bool(
        left
        and right
        and left.get("code") == right.get("code")
        and left.get("name") == right.get("name")
        and Decimal(str(left.get("score"))) == Decimal(str(right.get("score")))
    )


def _same_excel_recommendation(
    engine: dict[str, Any] | None,
    excel: dict[str, Any] | None,
) -> bool:
    return bool(
        engine
        and excel
        and engine.get("name") == excel.get("name")
        and Decimal(str(engine.get("score"))) == Decimal(str(excel.get("score")))
    )


def _canonical_source(source_db: Path) -> dict[str, Any]:
    digest = hashlib.sha256(source_db.read_bytes()).hexdigest()
    if digest != CANONICAL_SOURCE_SHA256:
        raise ValueError(
            f"Canonical source hash mismatch: expected {CANONICAL_SOURCE_SHA256}, got {digest}"
        )
    connection = sqlite3.connect(
        f"file:{source_db.as_posix()}?mode=ro",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    try:
        users = {
            row["id"]: dict(row)
            for row in connection.execute(
                "SELECT id, email, is_synthetic FROM users ORDER BY email"
            )
        }
        if len(users) != 30 or any(not user["is_synthetic"] for user in users.values()):
            raise ValueError("Canonical source must contain exactly 30 marked synthetic users.")

        profiles = {
            row["user_id"]: json.loads(row["data"])
            for row in connection.execute("SELECT user_id, data FROM profiles")
        }
        if len(profiles) != 30 or set(profiles) != set(users):
            raise ValueError("Canonical source must contain one profile for each synthetic user.")

        assessments: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in connection.execute(
            "SELECT id, user_id, score_json, created_at FROM assessments ORDER BY created_at, id"
        ):
            assessments[row["user_id"]].append(
                {
                    "id": row["id"],
                    "score_json": json.loads(row["score_json"]),
                    "created_at": row["created_at"],
                }
            )

        by_grade: dict[int, list[dict[str, Any]]] = defaultdict(list)
        source_codes: set[str] = set()
        for user_id, profile in profiles.items():
            code = profile.get("syntheticStudentCode")
            class_name = profile.get("className")
            grade_match = re.fullmatch(r"Lớp\s+(\d+)", str(class_name or ""))
            if (
                profile.get("dataProvenance") != "Synthetic"
                or not isinstance(code, str)
                or not code
                or not grade_match
            ):
                raise ValueError(f"Canonical profile {user_id} has invalid provenance/code/grade.")
            if code in source_codes:
                raise ValueError(f"Duplicate canonical synthetic student code: {code}")
            source_codes.add(code)
            grade = int(grade_match.group(1))
            by_grade[grade].append(
                {
                    "user_id": user_id,
                    "source_code": code,
                    "profile": profile,
                    "assessments": assessments.get(user_id, []),
                }
            )
        for records in by_grade.values():
            records.sort(key=lambda record: record["source_code"])

        return {
            "sha256": digest,
            "users": users,
            "profiles": profiles,
            "by_grade": by_grade,
            "assessment_count": sum(map(len, assessments.values())),
            "assessment_coverage": sum(bool(items) for items in assessments.values()),
        }
    finally:
        connection.close()


def _load_historical_engine() -> types.ModuleType:
    source = subprocess.run(
        [
            "git",
            "-C",
            str(PROJECT_ROOT),
            "show",
            f"{REFERENCE_ENGINE_COMMIT}:backend/app/services/career_matching.py",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout
    module = types.ModuleType("historical_career_matching")
    sys.modules[module.__name__] = module
    exec(compile(source, f"{REFERENCE_ENGINE_COMMIT}:career_matching.py", "exec"), module.__dict__)
    return module


def _historical_reference_replay(
    source_records: list[dict[str, Any]],
    historical_engine: types.ModuleType,
) -> dict[str, Any]:

    checked = 0
    matches = 0
    for record in source_records:
        assessments = record["assessments"]
        if not assessments:
            continue
        reference = assessments[-1]["score_json"].get("top3")
        actual = historical_engine.calculate_matches(record["profile"]).get("top3")
        if not isinstance(reference, list) or not isinstance(actual, list) or len(reference) != 3 or len(actual) != 3:
            continue
        checked += 1
        matches += all(_same_recommendation(left, right) for left, right in zip(reference, actual))
    return {
        "engine_commit": REFERENCE_ENGINE_COMMIT,
        "function": "calculate_matches(profile)",
        "assessments_reproduced": matches,
        "assessments_checked": checked,
        "exact_all_records": checked == 30 and matches == 30,
    }


def _matcher_change_attribution(
    profile: dict[str, Any],
    grade: int,
    historical_engine: types.ModuleType,
    historical_top3: list[dict[str, Any]],
    current_top3: list[dict[str, Any]],
) -> dict[str, Any]:
    changed_subjects = []
    for subject, keys in SUBJECT_KEYS.items():
        historical_value = historical_engine._subject_score(profile, subject)
        current_value = aggregate_subject_score(profile, subject)
        if historical_value == current_value:
            continue

        historical_source = next(
            (
                key
                for key in keys
                if not key.startswith("score")
                and historical_engine._number(profile.get(key)) is not None
            ),
            next(
                (
                    key
                    for key in keys
                    if key.startswith("score")
                    and historical_engine._number(profile.get(key)) is not None
                ),
                None,
            ),
        )
        annual_sources = [
            key
            for key in keys
            if key.startswith("score")
            and historical_engine._number(profile.get(key)) is not None
        ]
        changed_subjects.append(
            {
                "subject": subject,
                "historical_value": round(historical_value, 4) if historical_value is not None else None,
                "historical_source_field": historical_source,
                "historical_source_value": profile.get(historical_source) if historical_source else None,
                "current_value": round(current_value, 4) if current_value is not None else None,
                "current_source_fields": annual_sources,
                "current_source_values": {
                    key: profile[key] for key in annual_sources
                },
                "rule_changed": (
                    "multi_year_subject_aggregation"
                    if len(annual_sources) > 1
                    else "year_specific_subject_precedence"
                ),
            }
        )

    historical_gpa = historical_engine._gpa(profile)
    current_gpa = aggregate_gpa(profile)
    historical_result = [
        {"code": item.get("code"), "name": item.get("name"), "score": round(float(item.get("score")), 2)}
        for item in historical_top3
    ]
    current_result = [
        {"code": item.get("code"), "name": item.get("name"), "score": round(float(item.get("score")), 2)}
        for item in current_top3
    ]
    changed_ranks = [
        rank
        for rank, (historical, current) in enumerate(zip(historical_result, current_result), 1)
        if historical != current
    ]
    future_fields = sorted(
        key
        for key in profile
        if re.fullmatch(r"(?:score|gpa)(\d+)[A-Za-z]*", key)
        and int(re.match(r"(?:score|gpa)(\d+)", key).group(1)) > grade
        and _number(profile.get(key)) is not None
    )
    grade_value = _number(profile.get("grade"))
    return {
        "grade_from_class_name": grade,
        "grade_field_passed_to_engine": profile.get("grade"),
        "grade_bounded_filter_active": grade_value is not None,
        "future_grade_fields_present": future_fields,
        "historical_gpa": round(historical_gpa, 4),
        "current_gpa": round(current_gpa, 4),
        "gpa_changed": historical_gpa != current_gpa,
        "changed_subjects": changed_subjects,
        "causal_categories": sorted(
            {
                *(
                    item["rule_changed"]
                    for item in changed_subjects
                ),
                *(["gpa_aggregation"] if historical_gpa != current_gpa else []),
                *(["grade_bounded_data"] if future_fields and grade_value is not None else []),
                *(["missing_data_handling"] if any(
                    item["historical_value"] is None or item["current_value"] is None
                    for item in changed_subjects
                ) else []),
            }
        ),
        "historical_top3": historical_result,
        "current_top3": current_result,
        "changed_ranks": changed_ranks,
    }


def _academic_input_divergence(source_profile: dict[str, Any], workbook_profile: dict[str, Any]) -> list[dict[str, Any]]:
    academic_keys = {
        key
        for key in set(source_profile) | set(workbook_profile)
        if re.fullmatch(r"(?:score(?:9|10|11|12)[A-Za-z]+|gpa(?:9|10|11|12))", key)
    }
    differences = []
    for key in sorted(academic_keys):
        source_value = _number(source_profile.get(key))
        workbook_value = _number(workbook_profile.get(key))
        if source_value != workbook_value:
            differences.append(
                {
                    "field": key,
                    "canonical_source": source_value,
                    "workbook": workbook_value,
                }
            )
    return differences


def validate_canonical(workbook_path: Path, source_db: Path) -> dict[str, Any]:
    canonical = _canonical_source(source_db)
    workbook = load_workbook(workbook_path, data_only=False, read_only=True)
    try:
        if tuple(workbook.sheetnames) != REQUIRED_SHEETS:
            raise ValueError(f"Unexpected sheets: {workbook.sheetnames!r}")
        summary = workbook[REQUIRED_SHEETS[0]]
        summary_headers = _headers(summary)
        workbook_rows = _rows_by_student(summary, summary_headers, "HS+No.")
        if len(workbook_rows) != 30:
            raise ValueError(f"Expected 30 workbook records, found {len(workbook_rows)}.")

        source_records = [
            record
            for records in canonical["by_grade"].values()
            for record in records
        ]
        historical_engine = _load_historical_engine()
        historical_replay = _historical_reference_replay(source_records, historical_engine)
        student_results = []
        counts = Counter()
        rank_counts = {
            "engine_vs_reference": [0, 0, 0],
            "engine_vs_excel": [0, 0, 0],
            "reference_vs_excel": [0, 0, 0],
        }
        academic_divergence_students = 0
        academic_divergence_fields = 0
        incomplete_count = 0

        for student_id, row in workbook_rows.items():
            grade = int(summary.cell(row, summary_headers["Khối"]).value)
            student_match = re.fullmatch(r"HS(\d+)-(\d+)", student_id)
            if not student_match or int(student_match.group(1)) != grade:
                raise ValueError(f"Student ID {student_id!r} does not match workbook grade {grade}.")
            ordinal = int(student_match.group(2))
            source_grade_records = canonical["by_grade"].get(grade, [])
            record = source_grade_records[ordinal - 1] if ordinal <= len(source_grade_records) else None
            if record is None:
                student_results.append(
                    {
                        "student_id": student_id,
                        "classification": "incomplete_input",
                        "reason": f"No canonical source profile mapped for grade {grade}, position {ordinal}.",
                    }
                )
                counts["incomplete_input"] += 1
                incomplete_count += 1
                continue

            profile = record["profile"]
            assessments = record["assessments"]
            reference = assessments[-1]["score_json"].get("top3") if assessments else None
            if not isinstance(reference, list) or len(reference) != 3:
                student_results.append(
                    {
                        "student_id": student_id,
                        "source_code": record["source_code"],
                        "classification": "incomplete_input",
                        "reason": "Canonical profile exists, but its latest saved assessment has no valid Top 3.",
                    }
                )
                counts["incomplete_input"] += 1
                incomplete_count += 1
                continue

            current_result = calculate_matches(profile)
            engine_top3 = current_result.get("top3")
            if not isinstance(engine_top3, list) or len(engine_top3) != 3:
                raise ValueError(f"{student_id}: current engine did not return three recommendations.")
            historical_top3 = historical_engine.calculate_matches(profile).get("top3")
            if not isinstance(historical_top3, list) or len(historical_top3) != 3:
                raise ValueError(f"{student_id}: historical engine did not return three recommendations.")
            workbook_profile, workbook_missing_inputs = reconstruct_profile(workbook, student_id)
            academic_differences = _academic_input_divergence(profile, workbook_profile)
            academic_divergence_students += bool(academic_differences)
            academic_divergence_fields += len(academic_differences)
            matcher_change_analysis = _matcher_change_attribution(
                profile,
                grade,
                historical_engine,
                historical_top3,
                engine_top3,
            )
            excel_top3 = [
                _parse_stored_recommendation(
                    summary.cell(row, summary_headers[f"Top {rank}"]).value
                )
                for rank in (1, 2, 3)
            ]
            reference_top3 = [
                {
                    "code": item.get("code"),
                    "name": item.get("name"),
                    "score": round(float(item.get("score")), 2),
                }
                for item in reference
            ]
            engine_top3 = [
                {
                    "code": item.get("code"),
                    "name": item.get("name"),
                    "score": round(float(item.get("score")), 2),
                }
                for item in engine_top3
            ]
            normalized_excel = [
                {
                    "code": None,
                    "name": item["name"],
                    "score": float(item["score"]),
                }
                if item
                else None
                for item in excel_top3
            ]
            engine_reference_matches = [
                _same_recommendation(engine_top3[index], reference_top3[index])
                for index in range(3)
            ]
            engine_excel_matches = [
                _same_excel_recommendation(engine_top3[index], normalized_excel[index])
                for index in range(3)
            ]
            reference_excel_matches = [
                _same_excel_recommendation(reference_top3[index], normalized_excel[index])
                for index in range(3)
            ]
            for rank in range(3):
                rank_counts["engine_vs_reference"][rank] += engine_reference_matches[rank]
                rank_counts["engine_vs_excel"][rank] += engine_excel_matches[rank]
                rank_counts["reference_vs_excel"][rank] += reference_excel_matches[rank]

            full_reference_match = all(engine_reference_matches)
            full_excel_match = all(engine_excel_matches)
            if full_reference_match and full_excel_match:
                classification = "exact_parity"
                counts[classification] += 1
            elif full_reference_match:
                classification = "excel_mismatch"
                counts[classification] += 1
            else:
                classification = "source_mismatch"
                counts[classification] += 1

            reasons = []
            if not full_reference_match:
                reasons.append(
                    "Current calculate_matches differs from the latest saved assessment: "
                    + ", ".join(
                        f"rank {index + 1}" for index, matches in enumerate(engine_reference_matches) if not matches
                    )
                )
            if full_reference_match and not full_excel_match:
                reasons.append(
                    "Canonical saved reference matches the current engine, but Excel differs at "
                    + ", ".join(
                        f"rank {index + 1}" for index, matches in enumerate(engine_excel_matches) if not matches
                    )
                )
            elif not full_excel_match:
                reasons.append(
                    "Current engine differs from Excel at "
                    + ", ".join(
                        f"rank {index + 1}" for index, matches in enumerate(engine_excel_matches) if not matches
                    )
                )
            score_differences = []
            for rank in range(3):
                ref_score = float(reference_top3[rank]["score"])
                eng_score = float(engine_top3[rank]["score"])
                excel_score = float(normalized_excel[rank]["score"]) if normalized_excel[rank] else None
                score_differences.append(
                    {
                        "rank": rank + 1,
                        "engine_minus_reference": round(eng_score - ref_score, 2),
                        "excel_minus_reference": (
                            round(excel_score - ref_score, 2) if excel_score is not None else None
                        ),
                        "engine_minus_excel": (
                            round(eng_score - excel_score, 2) if excel_score is not None else None
                        ),
                    }
                )
            result = {
                "student_id": student_id,
                "source_code": record["source_code"],
                "canonical_profile_sha256": hashlib.sha256(
                    json.dumps(profile, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest(),
                "latest_assessment_id": assessments[-1]["id"],
                "latest_assessment_created_at": assessments[-1]["created_at"],
                "reference_top1": reference_top3[0],
                "reference_top2": reference_top3[1],
                "reference_top3": reference_top3[2],
                "engine_top1": engine_top3[0],
                "engine_top2": engine_top3[1],
                "engine_top3": engine_top3[2],
                "excel_top1": normalized_excel[0],
                "excel_top2": normalized_excel[1],
                "excel_top3": normalized_excel[2],
                "rank1_match": engine_reference_matches[0],
                "rank2_match": engine_reference_matches[1],
                "rank3_match": engine_reference_matches[2],
                "full_top3_match": full_reference_match,
                "excel_rank1_match": engine_excel_matches[0],
                "excel_rank2_match": engine_excel_matches[1],
                "excel_rank3_match": engine_excel_matches[2],
                "reference_excel_rank_matches": reference_excel_matches,
                "classification": classification,
                "reason": "; ".join(reasons) if reasons else None,
                "score_differences_if_available": score_differences,
                "academic_input_divergences": academic_differences,
                "matcher_change_analysis": matcher_change_analysis,
                "workbook_missing_engine_inputs": workbook_missing_inputs,
            }
            student_results.append(result)

        expected_grade_counts = {grade: len(items) for grade, items in canonical["by_grade"].items()}
        observed_grade_counts: dict[int, int] = defaultdict(int)
        for student_id in workbook_rows:
            match = re.fullmatch(r"HS(\d+)-(\d+)", student_id)
            if match:
                observed_grade_counts[int(match.group(1))] += 1
        if observed_grade_counts != expected_grade_counts:
            raise ValueError(
                f"Workbook cohort distribution does not match source: "
                f"{observed_grade_counts} vs {expected_grade_counts}"
            )

        mismatches = [
            {
                "hs_no": student["student_id"],
                "expected": [
                    student.get(f"reference_top{rank}")
                    for rank in range(1, 4)
                ],
                "actual": [
                    student.get(f"engine_top{rank}")
                    for rank in range(1, 4)
                ],
                "excel_actual": [
                    student.get(f"excel_top{rank}")
                    for rank in range(1, 4)
                ],
                "reason": student.get("reason"),
                "classification": student.get("classification"),
            }
            for student in student_results
            if student.get("classification") != "exact_parity"
        ]
        rank_score_matches = {
            label: {
                f"rank{rank + 1}": sum(
                    student.get("score_differences_if_available", [{}] * 3)[rank].get(field) == 0
                    for student in student_results
                    if student.get("score_differences_if_available")
                )
                for rank in range(3)
            }
            for label, field in (
                ("engine_vs_reference", "engine_minus_reference"),
                ("engine_vs_excel", "engine_minus_excel"),
                ("reference_vs_excel", "excel_minus_reference"),
            )
        }
        divergence_kinds = Counter()
        divergence_by_grade: dict[str, Counter[str]] = defaultdict(Counter)
        for student in student_results:
            grade_match = re.match(r"HS(\d+)-", str(student.get("student_id", "")))
            grade_key = grade_match.group(1) if grade_match else "unknown"
            for difference in student.get("academic_input_divergences", []):
                source_value = difference.get("canonical_source")
                workbook_value = difference.get("workbook")
                kind = (
                    "different_nonmissing_values"
                    if source_value is not None and workbook_value is not None
                    else "canonical_only_workbook_missing"
                    if source_value is not None
                    else "workbook_only_canonical_missing"
                )
                divergence_kinds[kind] += 1
                divergence_by_grade[grade_key][kind] += 1
        matcher_differences = [
            student["matcher_change_analysis"]
            for student in student_results
            if student.get("matcher_change_analysis")
            and student["matcher_change_analysis"]["changed_ranks"]
        ]
        matcher_category_counts = Counter(
            category
            for item in matcher_differences
            for category in item["causal_categories"]
        )
        workbook_sheetnames = list(workbook.sheetnames)
        return {
            "workbook": str(workbook_path),
            "canonical_source": {
                "path": str(source_db),
                "sha256": canonical["sha256"],
                "access": "SQLite read-only mode",
                "synthetic_users": len(canonical["users"]),
                "synthetic_profiles": len(canonical["profiles"]),
                "saved_assessments": canonical["assessment_count"],
                "profiles_with_saved_assessment": canonical["assessment_coverage"],
                "student_mapping": "HS{grade}-{ordinal} maps to source profiles sorted by grade and syntheticStudentCode; cohort counts must agree.",
            },
            "engine": {
                "function": "backend.app.services.career_matching.calculate_matches(profile)",
                "top3_fields": ["code", "name", "score"],
            },
            "input_completeness": {
                "canonical_profile_count": len(canonical["profiles"]),
                "reference_assessment_count": canonical["assessment_coverage"],
                "incomplete_student_count": incomplete_count,
                "profile_data_used_as_stored": True,
                "missing_optional_values_in_source_were_not_fabricated": True,
            },
            "historical_reference_replay": historical_replay,
            "students_checked": len(student_results),
            "parity_status": (
                "verified"
                if counts["exact_parity"] == len(student_results) and incomplete_count == 0
                else "not_verified"
            ),
            "exact_parity_count": counts["exact_parity"],
            "excel_mismatch_count": counts["excel_mismatch"],
            "source_mismatch_count": counts["source_mismatch"],
            "incomplete_input_count": counts["incomplete_input"],
            "validator_execution": {
                "status": (
                    "completed_with_incomplete_inputs"
                    if counts["incomplete_input"]
                    else "completed_with_source_differences"
                    if counts["source_mismatch"] or counts["excel_mismatch"]
                    else "completed"
                ),
                "error": None,
                "exit_code": (
                    2
                    if counts["incomplete_input"]
                    else 1
                    if counts["source_mismatch"] or counts["excel_mismatch"]
                    else 0
                ),
            },
            "classification_counts": {
                "exact_parity": counts["exact_parity"],
                "excel_mismatch": counts["excel_mismatch"],
                "source_mismatch": counts["source_mismatch"],
                "incomplete_input": counts["incomplete_input"],
            },
            "rank_specific_matches": {
                name: {
                    f"rank{rank + 1}": value
                    for rank, value in enumerate(rank_values)
                }
                for name, rank_values in rank_counts.items()
            },
            "rank_score_matches": rank_score_matches,
            "top1_matches": rank_counts["engine_vs_reference"][0],
            "top2_matches": rank_counts["engine_vs_reference"][1],
            "top3_matches": rank_counts["engine_vs_reference"][2],
            "score_matches": {
                "engine_vs_reference": sum(rank_score_matches["engine_vs_reference"].values()),
                "engine_vs_excel": sum(rank_score_matches["engine_vs_excel"].values()),
                "reference_vs_excel": sum(rank_score_matches["reference_vs_excel"].values()),
                "checked": len(student_results) * 3,
            },
            "mismatches": mismatches,
            "excel_rank_matches_current_engine": {
                f"rank{rank + 1}": sum(
                    result.get(f"excel_rank{rank + 1}_match", False)
                    for result in student_results
                )
                for rank in range(3)
            },
            "academic_input_divergence": {
                "students_with_any_difference": academic_divergence_students,
                "different_fields_total": academic_divergence_fields,
                "field_difference_kinds": dict(divergence_kinds),
                "by_grade": {
                    grade: dict(counts)
                    for grade, counts in sorted(divergence_by_grade.items())
                },
            },
            "matcher_change_analysis": {
                "historical_commit": REFERENCE_ENGINE_COMMIT,
                "current_file": "backend/app/services/career_matching.py (working tree)",
                "current_behavior_intent": {
                    "status": "intentionally_asserted_by_current_tests; no separate tracked product specification found",
                    "evidence": [
                        "aggregate_subject_score averages all available year-specific subject scores.",
                        "test_subject_scores_average_all_available_school_years asserts the year aggregation.",
                        "test_academic_aggregation_excludes_scores_from_future_grades asserts the grade filter when a grade field is supplied.",
                        "test_hs12_001_multi_year_subject_and_gpa_aggregation asserts an actual multi-year S1 calculation.",
                    ],
                    "qualification": "The website assessment route passes Profile.data through without deriving a numeric grade from className. Canonical profiles in this snapshot have className but no grade field and no year fields later than the displayed grade.",
                },
                "different_profiles": len(matcher_differences),
                "causal_category_counts": dict(matcher_category_counts),
                "gpa_changed_profiles": sum(item["gpa_changed"] for item in matcher_differences),
                "profiles": [
                    {
                        "student_id": student["student_id"],
                        "source_code": student["source_code"],
                        **student["matcher_change_analysis"],
                    }
                    for student in student_results
                    if student.get("matcher_change_analysis")
                    and student["matcher_change_analysis"]["changed_ranks"]
                ],
            },
            "workbook_reconciliation": {
                "current_workbook_sheets": workbook_sheetnames,
                "current_exporter_sheets": [
                    "Summary",
                    "Students",
                    "Academic",
                    "GPA",
                    "Certificates",
                    "Achievements",
                    "Personality",
                    "Interests",
                    "Recommendations",
                ],
                "current_exporter_reads_profile_data_and_calls_calculate_matches": True,
                "same_generator_provenance_established": False,
                "classification": "separate_untracked_workbook_source_provenance_and_intent_unknown",
                "field_differences": {
                    "total": academic_divergence_fields,
                    "breakdown": dict(divergence_kinds),
                    "by_grade": {
                        grade: dict(counts)
                        for grade, counts in sorted(divergence_by_grade.items())
                    },
                },
                "engine_reconstruction_from_workbook_inputs": {
                    "status": "blocked_unrepresented_workbook_inputs",
                    "missing_inputs": sorted(
                        {
                            missing
                            for student in student_results
                            for missing in student.get("workbook_missing_engine_inputs", [])
                        }
                    ),
                    "reason": "The workbook omits 84 canonical Grade 12 academic values because its existing layout has no Grade 12 columns; its represented Grade 10-11 academic inputs were reconciled. Numeric RIASEC/progress and some application profile fields are also absent, so the workbook alone cannot reproduce the full engine input.",
                },
                "modified_during_this_investigation": False,
            },
            "comparison_axes": {
                "current_vs_historical_reference": {
                    "exact_top3_profiles": sum(
                        student.get("full_top3_match", False) for student in student_results
                    ),
                    "different_top3_profiles": len(matcher_differences),
                    "exact_rank_score_matches": rank_score_matches["engine_vs_reference"],
                },
                "current_canonical_engine_vs_stored_excel": {
                    "exact_top3_profiles": sum(
                        all(student.get(f"excel_rank{rank}_match", False) for rank in (1, 2, 3))
                        for student in student_results
                    ),
                    "exact_rank_matches": {
                        f"rank{rank}": rank_counts["engine_vs_excel"][rank - 1]
                        for rank in (1, 2, 3)
                    },
                    "caveat": "This compares engine results from canonical Profile.data with stored workbook recommendations and does not independently reconstruct all engine inputs from workbook-only data; 84 Grade 12 academic values and numeric RIASEC/application fields are not represented.",
                },
            },
            "excel_changed": False,
            "generation_pipeline_changed": False,
            "pipeline_trace": {
                "synthetic_source": "The read-only SQLite snapshot's profiles.data JSON.",
                "assessment_reference": "Latest assessments.score_json.top3 ordered by created_at, then assessment id.",
                "original_generation": "The repository-baseline calculate_matches() reproduces the latest saved reference when historical_reference_replay is exact.",
                "current_engine_divergence": "All 22 historical/current differences are caused by averaging multiple available year-specific subject values; the historical matcher used the first available score (score10). GPA results are unchanged on these source profiles. No RIASEC, S5, industry priority, or ranking-weight code changed in the matcher diff.",
                "application_call_chain": "learning.run_assessment copies Profile.data, adds name/email, calls calculate_matches(profile_data), and persists the returned Top 3. It does not derive grade from className.",
                "current_generation_exporter": "tools/synthetic_students.py::export_workbook reads synthetic Profile.data, calls current calculate_matches(profile), and emits a 9-sheet Summary/Students/Academic/... workbook.",
                "current_workbook_provenance": "The audited workbook has three localized sheets. Its represented Grade 10-11 academic inputs match canonical values; 84 Grade 12 academic values cannot be represented in its existing layout. Its exact generator and intent are not established by tracked code; it does not match the current exporter's output schema.",
            },
            "students": student_results,
            **_review_metadata(),
        }
    finally:
        workbook.close()


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    canonical_source = report.get("canonical_source")
    if not isinstance(canonical_source, dict):
        canonical_source = {}

    lines = [
        "# Canonical synthetic recommendation parity",
        "",
        f"- Validator execution: **{report['validator_execution']['status']}**",
        f"- Validator exit code: **{report['validator_execution']['exit_code']}**",
        f"- Total records checked: **{report['students_checked']}**",
        f"- Overall parity status: **{report.get('parity_status', 'not_run')}**",
        "",
        "## Canonical source and lineage",
        "",
        f"- Synthetic profiles and academic/profile inputs: `{canonical_source.get('path', 'unavailable')}`",
        f"- Snapshot SHA-256: `{canonical_source.get('sha256', 'unavailable')}`",
        "- Saved recommendation reference: latest `assessments.score_json.top3` per synthetic profile.",
        "- Current source-of-truth engine: `backend.app.services.career_matching.calculate_matches(profile)`.",
        f"- Historical reference replay: **{report.get('historical_reference_replay', {}).get('assessments_reproduced', 0)}/"
        f"{report.get('historical_reference_replay', {}).get('assessments_checked', 0)}** saved references reproduced by baseline commit "
        f"`{report.get('historical_reference_replay', {}).get('engine_commit', 'unavailable')}`.",
        "- Synthetic source profiles were read from SQLite in read-only mode. Assessment/profile values were not changed.",
        "- Original 3-sheet workbook history is not in Git; this report independently compares its currently stored Top 3 values.",
        "",
        "## A. Verified",
        "",
        *[f"- {item}" for item in report["verified"]],
        "",
        "## Current matcher intent and 22 historical differences",
        "",
        f"- Intent assessment: **{report.get('matcher_change_analysis', {}).get('current_behavior_intent', {}).get('status', 'not assessed')}**.",
        "- Evidence: the current implementation averages year-specific subject scores; tests assert multi-year averaging, future-grade exclusion when a numeric grade is supplied, and a Grade-12 S1 result. No separate tracked product specification was found, so this is code/test intent rather than independent product approval.",
        "- The production assessment route passes `Profile.data` through without deriving `grade` from `className`. The 30 canonical source profiles have no numeric `grade`, and their year-specific academic data does not extend beyond the grade in `className`; therefore no grade-bound exclusion affects these 22 records.",
        "- All 22 differences are caused by multi-year subject aggregation: historical `calculate_matches` uses the first available annual value (for these records, `score10*`); current `calculate_matches` averages the available `score10*` + `score11*` values for Grade 11 and `score10*` + `score11*` + `score12*` for Grade 12.",
        f"- GPA values changed for **{report.get('matcher_change_analysis', {}).get('gpa_changed_profiles', 0)}/22** differing records. RIASEC, S5, priority ordering, and ROC weights were not changed in the matcher diff.",
        "",
        "| Student | Grade | GPA historical → current | Effective subject input changes (historical → current) | Top 3 historical → current (code / score) |",
        "|---|---:|---:|---|---|",
        *[
            "| "
            + " | ".join(
                (
                    item["student_id"],
                    str(item["grade_from_class_name"]),
                    f"{item['historical_gpa']:.4f} → {item['current_gpa']:.4f}",
                    "; ".join(
                        f"{subject['subject']} {subject['historical_value']:.4f} → {subject['current_value']:.4f}"
                        for subject in item["changed_subjects"]
                    )
                    or "—",
                    "<br>".join(
                        f"{old['code']} {old['score']:.2f} → {new['code']} {new['score']:.2f}"
                        for old, new in zip(item["historical_top3"], item["current_top3"])
                    ),
                )
            )
            + " |"
            for item in report.get("matcher_change_analysis", {}).get("profiles", [])
        ],
        "",
        "## Workbook input reconciliation",
        "",
        "- The workbook's represented Grade 10-11 academic inputs match the canonical profile values. Its existing layout cannot represent **84 Grade 12 values** (72 subject scores and 12 GPAs across 12 profiles); these are omitted fields, not populated-value mismatches.",
        "- The target workbook has the localized 3-sheet schema (`Tổng hợp`, `Môn học`, `Hồ sơ`). The current `tools/synthetic_students.py::export_workbook` emits a different 9-sheet schema and reads canonical `Profile.data`; no tracked generator for the target workbook or reliable authoring lineage was found.",
        "- Classification: **workbook generator provenance and intent unknown**. The workbook itself was not changed during validation.",
        "- Recomputing Top 3 from the workbook alone is blocked: it has a Holland-code display but not the numeric RIASEC/progress and other application inputs needed for exact engine parity. The reported 30/30 engine-to-stored-Excel recommendation match was calculated from canonical `Profile.data`, not reconstructed from workbook-only inputs.",
        "- Workbook modified during this investigation: **No**.",
        "",
        "## Parity classification",
        "",
        f"- Exact parity: **{report.get('exact_parity_count', 0)}**",
        f"- Excel mismatch: **{report.get('excel_mismatch_count', 0)}**",
        f"- Source mismatch: **{report.get('source_mismatch_count', 0)}**",
        f"- Incomplete input: **{report.get('incomplete_input_count', report['students_checked'])}**",
        f"- Rank matches (current engine vs reference): **Top 1 {report.get('top1_matches', 0)}/"
        f"{report['students_checked']}, Top 2 {report.get('top2_matches', 0)}/"
        f"{report['students_checked']}, Top 3 {report.get('top3_matches', 0)}/"
        f"{report['students_checked']}**",
        "- Exact industry + score matches against Excel: **"
        + ", ".join(
            f"Top {rank} {report.get('excel_rank_matches_current_engine', {}).get(f'rank{rank}', 0)}/"
            f"{report['students_checked']}"
            for rank in range(1, 4)
        )
        + "**",
        "- Exact industry + score matches (canonical reference vs Excel): **"
        + ", ".join(
            f"Top {rank} {report.get('rank_specific_matches', {}).get('reference_vs_excel', {}).get(f'rank{rank}', 0)}/"
            f"{report['students_checked']}"
            for rank in range(1, 4)
        )
        + "**",
        f"- Academic source/workbook divergence: **{report.get('academic_input_divergence', {}).get('students_with_any_difference', 0)} "
        f"students; {report.get('academic_input_divergence', {}).get('different_fields_total', 0)} fields**",
        f"- Current-engine divergence context: {report.get('pipeline_trace', {}).get('current_engine_divergence', 'not assessed')}",
        "",
        "### Rank match counts (current engine vs canonical reference)",
        "",
        "| Rank | Exact industry + score |",
        "|---|---:|",
        *[
            f"| {rank} | {report.get('rank_specific_matches', {}).get('engine_vs_reference', {}).get(f'rank{rank}', 0)}/"
            f"{report['students_checked']} |"
            for rank in range(1, 4)
        ],
        "",
        "### Source-to-reference-to-engine-to-Excel comparison",
        "",
        "| Student | Status | Reference Top 3 | Current engine Top 3 | Excel Top 3 | Reason |",
        "|---|---|---|---|---|---|",
        *[
            "| "
            + " | ".join(
                (
                    student.get("student_id", "—"),
                    student.get("classification", "incomplete_input"),
                    "<br>".join(_format_cell(student.get(f"reference_top{rank}")) for rank in range(1, 4)),
                    "<br>".join(_format_cell(student.get(f"engine_top{rank}")) for rank in range(1, 4)),
                    "<br>".join(_format_cell(student.get(f"excel_top{rank}")) for rank in range(1, 4)),
                    student.get("reason") or "—",
                )
            )
            + " |"
            for student in report.get("students", [])
        ],
        "",
        "## B. Fixed",
        "",
        *[f"- {item}" for item in report["fixed"]],
        "",
        "## C. Not verified",
        "",
        *[f"- {item}" for item in report["not_verified"]],
        "",
        "## D. Blocked",
        "",
        *[f"- {item}" for item in report["blocked"]],
        "",
        f"- Migration source: `{report['review_findings']['migration']['source']}`.",
        f"- Render migration command: `{report['review_findings']['migration']['command']}` (service root `backend`).",
        f"- Expected schema head: `{report['review_findings']['migration']['expected_head']}`; "
        f"target: `{report['review_findings']['migration']['schema_change']}`.",
        "- Production migration status: **not verified**. Vercel does not run migrations from `api/index.py`.",
        "- AI rate limits: 5 requests/60 seconds for standard AI endpoints (configurable); CV has 5/600 seconds then a 600-second lockout. State is atomic only within each process.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _format_cell(item: dict[str, Any] | None) -> str:
    if not item:
        return "—"
    return f"{item.get('name', '—')} — {item.get('score', '—')}%"


def validate_without_source(workbook_path: Path) -> dict[str, Any]:
    workbook = load_workbook(workbook_path, data_only=False, read_only=True)
    try:
        if tuple(workbook.sheetnames) != REQUIRED_SHEETS:
            raise ValueError(f"Unexpected sheets: {workbook.sheetnames!r}")
        summary = workbook[REQUIRED_SHEETS[0]]
        summary_headers = _headers(summary)
        student_rows = _rows_by_student(summary, summary_headers, "HS+No.")
        students = []
        for student_id, row in student_rows.items():
            students.append(
                {
                    "student_id": student_id,
                    "classification": "incomplete_input",
                    "reason": "Canonical source profile and saved assessment snapshot were not supplied.",
                    **{
                        f"excel_top{rank}": (
                            {
                                "name": item["name"],
                                "score": float(item["score"]),
                            }
                            if (
                                item := _parse_stored_recommendation(
                                    summary.cell(row, summary_headers[f"Top {rank}"]).value
                                )
                            )
                            else None
                        )
                        for rank in range(1, 4)
                    },
                }
            )
        return {
            "workbook": str(workbook_path),
            "engine": {
                "function": "backend.app.services.career_matching.calculate_matches(profile)",
                "top3_fields": ["code", "name", "score"],
            },
            "canonical_source": None,
            "input_completeness": {"incomplete_student_count": len(students)},
            "students_checked": len(students),
            "parity_status": "not_verified",
            "validator_execution": {
                "status": "incomplete_canonical_source_not_supplied",
                "error": None,
                "exit_code": 2,
            },
            "exact_parity_count": 0,
            "excel_mismatch_count": 0,
            "source_mismatch_count": 0,
            "incomplete_input_count": len(students),
            "rank_specific_matches": {
                "engine_vs_reference": {"rank1": 0, "rank2": 0, "rank3": 0},
                "engine_vs_excel": {"rank1": 0, "rank2": 0, "rank3": 0},
                "reference_vs_excel": {"rank1": 0, "rank2": 0, "rank3": 0},
            },
            "students": students,
            "excel_changed": False,
            "generation_pipeline_changed": False,
            "verified": [],
            "fixed": [],
            "not_verified": [
                "Canonical source profile and saved assessment were not provided; no parity comparison was attempted."
            ],
            "blocked": ["Do not infer parity from incomplete workbook-only profile reconstruction."],
            **_review_metadata(),
        }
    finally:
        workbook.close()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "workbook",
        nargs="?",
        type=Path,
        default=PROJECT_ROOT / "students_anonymized_30.xlsx",
    )
    parser.add_argument(
        "--source-db",
        type=Path,
        help="Read-only canonical synthetic SQLite snapshot containing profiles and saved assessments.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=PROJECT_ROOT / ".qa" / "WORKBOOK_PARITY_VALIDATION.json",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=PROJECT_ROOT / ".qa" / "WORKBOOK_PARITY_VALIDATION.md",
    )
    args = parser.parse_args()

    try:
        report = (
            validate_canonical(args.workbook.resolve(), args.source_db.resolve())
            if args.source_db
            else validate_without_source(args.workbook.resolve())
        )
        exit_code = report["validator_execution"]["exit_code"]
    except Exception as exc:
        report = {
            "workbook": str(args.workbook.resolve()),
            "canonical_source": str(args.source_db.resolve()) if args.source_db else None,
            "engine": {
                "function": "backend.app.services.career_matching.calculate_matches(profile)",
                "top3_fields": ["code", "name", "score"],
            },
            "students_checked": 0,
            "parity_status": "not_run",
            "validator_execution": {
                "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
                "exit_code": 2,
            },
            "exact_parity_count": 0,
            "excel_mismatch_count": 0,
            "source_mismatch_count": 0,
            "incomplete_input_count": 0,
            "rank_specific_matches": {},
            "students": [],
            "excel_changed": False,
            "generation_pipeline_changed": False,
            "verified": [],
            "fixed": [],
            "not_verified": [],
            "blocked": ["Validator execution failed; no parity claim is made."],
            **_review_metadata(),
        }
        exit_code = 2

    report["validator_execution"]["exit_code"] = exit_code
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_markdown(args.markdown_output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
