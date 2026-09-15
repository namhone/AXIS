from __future__ import annotations

from typing import Any


SKILL_TRACKS: dict[str, list[dict[str, Any]]] = {
    "N01": [
        {
            "id": "python-foundations",
            "name": "Python nền tảng",
            "why": "Ngôn ngữ đầu tiên để rèn tư duy lập trình và tạo sản phẩm nhỏ.",
            "modules": ["biến và kiểu dữ liệu", "điều kiện và vòng lặp", "hàm", "list/dict", "đọc ghi file"],
            "evidence": "Hoàn thành 20 bài cơ bản và một chương trình quản lý dữ liệu nhỏ.",
        },
        {
            "id": "cpp-foundations",
            "name": "C++ và thuật toán cơ bản",
            "why": "Tạo nền cho cấu trúc dữ liệu, giải thuật và các bài thi lập trình.",
            "modules": ["cú pháp", "mảng và chuỗi", "hàm", "sắp xếp", "tìm kiếm"],
            "evidence": "Giải 15 bài và viết chú thích giải thích độ phức tạp.",
        },
        {
            "id": "math-logic",
            "name": "Toán và tư duy logic",
            "why": "Hỗ trợ phân tích bài toán trước khi viết mã.",
            "modules": ["mệnh đề", "tổ hợp", "xác suất cơ bản", "suy luận và mô hình hóa"],
            "evidence": "Làm 2 bộ bài tập/tuần và tự viết hướng giải cho 5 bài.",
        },
        {
            "id": "project-practice",
            "name": "Dự án công nghệ nhỏ",
            "why": "Biến kiến thức thành sản phẩm có thể đưa vào portfolio.",
            "modules": ["Git", "đọc tài liệu", "thiết kế yêu cầu", "debug", "viết README"],
            "evidence": "Một sản phẩm chạy được, có Git history và README.",
        },
        {
            "id": "technical-english",
            "name": "Tiếng Anh kỹ thuật",
            "why": "Đọc documentation và tiếp cận tài liệu chuẩn.",
            "modules": ["từ vựng code", "đọc documentation", "viết issue/README"],
            "evidence": "Tóm tắt 3 tài liệu kỹ thuật bằng tiếng Anh.",
        },
    ],
    "default": [
        {
            "id": "core-subject",
            "name": "Môn cốt lõi của ngành",
            "why": "Củng cố môn học có ảnh hưởng trực tiếp đến nhóm ngành phù hợp nhất.",
            "modules": ["ôn nền tảng", "bài tập theo chuyên đề", "đề kiểm tra ngắn"],
            "evidence": "Một bộ bài tập có đáp án và nhật ký lỗi sai mỗi tuần.",
        },
        {
            "id": "communication",
            "name": "Giao tiếp và trình bày",
            "why": "Giúp giải thích ý tưởng, sản phẩm và kết quả học tập.",
            "modules": ["tóm tắt", "thuyết trình ngắn", "phản biện"],
            "evidence": "Một bài trình bày 5 phút có dàn ý và bản tự đánh giá.",
        },
        {
            "id": "project-practice",
            "name": "Dự án thực hành",
            "why": "Tạo bằng chứng cụ thể thay vì chỉ ghi mục tiêu chung chung.",
            "modules": ["chọn vấn đề", "lập kế hoạch", "thực hiện", "đánh giá"],
            "evidence": "Một sản phẩm hoặc báo cáo có phiên bản trước/sau.",
        },
    ],
}


def _top_career_code(profile: dict[str, Any]) -> str:
    matches = profile.get("career_matches")
    if isinstance(matches, list) and matches:
        first = matches[0]
        if isinstance(first, dict):
            return str(first.get("code") or first.get("industry_code") or "default")
    return "default"


def _weeks_until_grade_12(profile: dict[str, Any]) -> int:
    raw = profile.get("className") or profile.get("grade") or profile.get("class_level")
    try:
        grade = int(str(raw).strip().lower().replace("lớp", "").strip())
    except ValueError:
        grade = 10
    return max(8, min(72, (12 - max(10, min(12, grade))) * 36))


def build_skill_plan(profile: dict[str, Any]) -> dict[str, Any]:
    code = _top_career_code(profile)
    source = SKILL_TRACKS.get(code, SKILL_TRACKS["default"])
    weeks = _weeks_until_grade_12(profile)
    default_minutes = int(profile.get("studyMinutesPerDay") or profile.get("minutesPerDay") or 45)
    minutes = max(15, min(180, default_minutes))
    tracks: list[dict[str, Any]] = []
    for index, skill in enumerate(source, start=1):
        suggested_weeks = max(2, round(weeks / len(source)))
        tracks.append(
            {
                **skill,
                "order": index,
                "suggested_weeks": suggested_weeks,
                "minutes_per_day": minutes,
                "checks": [
                    "Bài kiểm tra 10 câu sau mỗi module",
                    "Một bài thực hành có đầu ra",
                    "Ôn lại lỗi sai trước khi mở module tiếp theo",
                ],
            }
        )
    saved_order = profile.get("skillOrder")
    if isinstance(saved_order, list):
        positions = {str(value): index for index, value in enumerate(saved_order)}
        tracks.sort(key=lambda item: positions.get(item["id"], len(positions) + item["order"]))
    return {
        "career_code": code,
        "weeks_until_grade_12": weeks,
        "daily_minutes": minutes,
        "tracks": tracks,
        "grade_12_mode": {
            "title": "Lớp 12: học song song và giữ nhịp",
            "description": "Sau khi vào lớp 12, chuyển sang các phiên ngắn 30–60 phút, ưu tiên ôn thi chính khóa và duy trì một kỹ năng ngành mỗi ngày.",
            "weekly_pattern": ["3 buổi môn cốt lõi", "2 buổi kỹ năng ngành", "1 buổi bài kiểm tra", "1 buổi nghỉ/ôn lỗi sai"],
        },
    }
