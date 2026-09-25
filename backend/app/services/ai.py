import json
from typing import Any

from openai import OpenAI

from ..core.config import Settings


class AIService:
    """Generate structured learning content through the OpenAI API."""

    _VI_TO_EN = {
        "học sinh": "student",
        "sinh viên": "student",
        "hồ sơ": "profile",
        "giới thiệu": "profile",
        "mục tiêu": "objective",
        "kỹ năng": "skills",
        "kinh nghiệm": "experience",
        "học vấn": "education",
        "chứng chỉ": "certificates",
        "sở thích": "interests",
        "thành tích": "achievements",
        "điện thoại": "phone",
        "email": "email",
        "địa điểm": "location",
        "liên kết": "website",
        "dự án": "project",
        "cá nhân": "personal",
        "lớp": "class",
        "gpa": "GPA",
        "thành viên": "member",
        "trưởng ban": "team lead",
        "phòng": "department",
    }

    _EN_TO_VI = {
        "student": "học sinh",
        "profile": "hồ sơ",
        "objective": "mục tiêu",
        "skills": "kỹ năng",
        "experience": "kinh nghiệm",
        "education": "học vấn",
        "certificates": "chứng chỉ",
        "interests": "sở thích",
        "achievements": "thành tích",
        "phone": "điện thoại",
        "email": "email",
        "location": "địa điểm",
        "website": "liên kết",
        "project": "dự án",
        "member": "thành viên",
        "class": "lớp",
        "gpa": "GPA",
    }

    @staticmethod
    def _validate_school_task(task: dict[str, Any]) -> None:
        title = str(task.get("title") or "").lower()
        has_school_signal = any(token in title for token in ["toán", "văn", "lý", "hóa", "sinh", "anh", "sử", "địa", "tin", "bài", "chương", "hệ thức", "đại số", "hình học"])
        resources = task.get("resources") or []
        urls = [
            str(resource.get("url", ""))
            for resource in resources
            if isinstance(resource, dict) and isinstance(resource.get("url"), str)
        ]
        if has_school_signal and not urls:
            raise ValueError("School tasks must include at least one valid source URL")
        if any(term in title for term in ["cộng", "trừ", "nhân", "chia"]) and "lớp 9" in title:
            raise ValueError("Unsupported Grade 9 arithmetic lesson content")

    @staticmethod
    def _validate_steps(steps: list[dict[str, Any]]) -> None:
        for step in steps:
            for task in step.get("tasks") or []:
                if isinstance(task, dict):
                    AIService._validate_school_task(task)

    def __init__(self, settings: Settings) -> None:
        self._client = None
        if settings.groq_api_key:
            self._client = OpenAI(
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
            )
        self._model = settings.groq_model or "llama-3.1-8b-instant"

    @classmethod
    def _translate_tokens(cls, text: str, language: str) -> str:
        if not text:
            return text
        if language == "en":
            mapping = cls._VI_TO_EN
            target = "en"
        else:
            mapping = cls._EN_TO_VI
            target = "vi"

        lowered = text.lower()
        for source, replacement in sorted(mapping.items(), key=lambda item: len(item[0]), reverse=True):
            if source in lowered:
                lowered = lowered.replace(source, replacement)
        if lowered == text.lower() and target == "en":
            return text
        return lowered

    @classmethod
    def _normalize_text(cls, text: str) -> str:
        if not isinstance(text, str):
            return text
        return " ".join(text.strip().split())

    @classmethod
    def _fallback_cv_transform(cls, value: Any, language: str, operation: str) -> Any:
        if isinstance(value, dict):
            return {key: cls._fallback_cv_transform(item, language, operation) for key, item in value.items()}
        if isinstance(value, list):
            return [cls._fallback_cv_transform(item, language, operation) for item in value]
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return value
            if operation == "normalize":
                return cls._normalize_text(text)
            if operation == "translate":
                return cls._translate_tokens(text, language)
            return text
        return value

    def generate_cv(self, cv_data: dict[str, Any], language: str, operation: str) -> dict[str, Any]:
        """Translate/optimize CV content without exposing the provider key to clients."""
        if language not in {"vi", "en"}:
            raise ValueError("Unsupported CV language")
        if operation not in {"translate", "normalize"}:
            raise ValueError("Unsupported CV operation")
        payload = json.dumps(cv_data, ensure_ascii=False, default=str)
        if len(payload) > 16000:
            raise ValueError("CV content is too large")

        if self._client is None:
            fallback = self._fallback_cv_transform(cv_data, language, operation)
            if not isinstance(fallback, dict):
                raise ValueError("AI returned invalid CV content")
            return fallback

        instruction = (
            "Translate every human-written value to English" if language == "en"
            else "Translate every human-written value to Vietnamese"
        )
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You transform a CV data object. Return JSON only, with the exact same keys and "
                        "array/object shape as the input. " + instruction + ". "
                        "Never translate names, email addresses, phone numbers, URLs, scores, years, "
                        "proper product/company names, or certificate acronyms. Preserve facts and numbers. "
                        "Do not add claims or invent experience. Keep translated strings concise. "
                        + ("Improve grammar and concise professional wording while preserving facts. "
                           if operation == "normalize" else "")
                    ),
                },
                {"role": "user", "content": payload},
            ],
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("AI returned empty CV content")
        result = json.loads(content)
        if not isinstance(result, dict):
            raise ValueError("AI returned invalid CV content")
        return result

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
                        "Với môn học phổ thông, không được bịa kiến thức quá cơ bản hoặc gán sai lớp học. "
                        "Không viết chung chung như 'Sách giáo khoa lớp 9, trang 45-48'. Hãy tham khảo tên bài "
                        "và chủ đề thực tế từ VietJack (https://vietjack.com/) rồi ghi đúng tên bài trong title; "
                        "resources phải có URL VietJack cụ thể nếu nhiệm vụ là môn phổ thông. Nếu không xác định chắc "
                        "tên bài hoặc URL, hãy chọn một chủ đề phổ thông khác mà bạn biết chắc thay vì tự đoán. "
                        "Với môn học phổ thông, ưu tiên chủ đề phù hợp chương trình hiện tại và ghi nguồn tham khảo "
                        "ở trường resources. Với lập trình, chỉ dùng tài liệu "
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
            normalized_task_list = tasks if isinstance(tasks, list) else []
            self._validate_steps([
                {"tasks": normalized_task_list}
            ])
            normalized.append(
                {
                    "step_number": index,
                    "title": title.strip()[:255],
                    "content": content.strip() if isinstance(content, str) else "",
                    "tasks": normalized_task_list,
                }
            )
        return normalized
