import json
from typing import Any

from openai import OpenAI

from ..core.config import Settings


class AIService:
    """Generate structured learning content through the OpenAI API."""

    def __init__(self, settings: Settings) -> None:
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is not configured")
        self._client = OpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        self._model = settings.groq_model

    def generate_roadmap(self, profile: dict[str, Any], goals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=0.3,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Bạn là chuyên gia xây dựng thời khóa biểu học tập theo ngành nghề cho học sinh. "
                        "Đây chỉ là một tuần trong lộ trình dài hạn, không phải toàn bộ chương trình. "
                        "Không được tuyên bố học xong cả Python, C++, hay một lĩnh vực chỉ trong 7 ngày. "
                        "Hãy tạo đúng 7 ngày liên tiếp, một phần tử cho mỗi ngày, không gộp nhiều ngày. "
                        "Chỉ trả về JSON object có khóa steps, trong đó steps là mảng đúng 7 phần tử. "
                        "Mỗi phần tử có step_number (1-7), title và tasks. tasks là mảng tối đa 4 phần tử; "
                        "Mỗi task phải là một việc hành động độc lập, không lồng thêm danh sách subtask; "
                        "title phải bắt đầu bằng 'Ngày 1'...'Ngày 7' và mô tả kỹ năng cụ thể. "
                        "Mỗi task phải là nhiệm vụ học thật, làm được và kiểm tra được trong ngày: "
                        "nêu rõ môn/công cụ/chủ đề, bài tập hoặc sản phẩm đầu ra, số lượng tối thiểu "
                        "và thời lượng dự kiến. Không được dùng mục tiêu mơ hồ như build self-awareness, "
                        "develop mindset, explore interests hoặc improve yourself. "
                        "Mỗi ngày tối đa 4 task/môn và tổng thời gian không quá 180 phút. "
                        "Nếu cần nhiều bước, hãy trả mỗi bước như một task riêng, không chia nhỏ trong một task. "
                        "Ví dụ ngành Máy tính: tuần này chỉ học biến/kiểu dữ liệu hoặc vòng lặp Python, "
                        "không nhảy đồng thời qua toàn bộ Python và C++. Mỗi ngày tối đa một chủ đề mới; "
                        "dành ngày cuối để kiểm tra và sửa lỗi. "
                        "Với môn học phổ thông, ưu tiên chủ đề phù hợp chương trình hiện tại và ghi nguồn tham khảo "
                        "ở trường resources (sách giáo khoa/chương nếu biết chắc). Với lập trình, chỉ dùng tài liệu "
                        "chính thức hoặc uy tín như Python Docs, MDN, C++ Reference, Arduino Docs hoặc roadmap.sh; "
                        "không bịa liên kết. "
                        "Nếu đầu vào có career_matches, hãy ưu tiên nhóm ngành đứng đầu và chọn "
                        "kỹ năng nền tảng phù hợp với nhóm ngành đó. Nếu có skill_plan, phải bám vào "
                        "track đang đứng đầu, số tuần gợi ý và thời lượng mỗi ngày."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"profile": profile, "goals": goals},
                        ensure_ascii=False,
                        default=str,
                    ),
                },
            ],
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("OpenAI returned an empty roadmap")
        payload = json.loads(content)
        steps = payload.get("steps") if isinstance(payload, dict) else None
        if not isinstance(steps, list) or len(steps) != 7:
            raise ValueError("AI returned an invalid 7-day roadmap")

        normalized: list[dict[str, Any]] = []
        for index, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                raise ValueError("OpenAI returned an invalid roadmap step")
            title = step.get("title")
            content = step.get("content")
            tasks = step.get("tasks")
            if not isinstance(title, str) or not title.strip():
                raise ValueError("Roadmap step title is missing")
            if not isinstance(content, str) and not isinstance(tasks, list):
                raise ValueError("Roadmap step content is missing")
            normalized.append(
                {
                    "step_number": index,
                    "title": title.strip()[:255],
                    "content": content.strip() if isinstance(content, str) else "",
                    "tasks": tasks if isinstance(tasks, list) else [],
                }
            )
        return normalized
