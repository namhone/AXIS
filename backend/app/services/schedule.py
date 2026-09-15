from __future__ import annotations

import json
import uuid
from datetime import date, timedelta
from typing import Any

DAILY_LIMIT_MINUTES = 180
DAILY_TASK_LIMIT = 4
MAX_DEFERRALS = 3


def parse_step_content(content: str) -> dict[str, Any]:
    try:
        value = json.loads(content)
    except (TypeError, json.JSONDecodeError):
        return {"tasks": [{"title": content.strip(), "subtasks": [content.strip(), "Ghi lại kết quả và lỗi sai."]}]}
    return value if isinstance(value, dict) else {"tasks": []}


def _is_complete(task: Any) -> bool:
    return isinstance(task, dict) and (
        task.get("status") == "completed"
        or int(task.get("completion_percent", 0) or 0) >= 100
    )


def reconcile_overdue_steps(steps: list[Any], today: date | None = None) -> bool:
    """Move incomplete tasks from past days toward today, mutating ORM steps."""
    today = today or date.today()
    changed = False
    for index, step in enumerate(steps):
        schedule = parse_step_content(step.content)
        raw_date = schedule.get("date")
        try:
            step_date = date.fromisoformat(raw_date)
        except (TypeError, ValueError):
            continue
        if step_date >= today:
            continue
        tasks = schedule.get("tasks", [])
        pending = [task for task in tasks if not _is_complete(task)]
        if not pending:
            continue
        schedule["tasks"] = [task for task in tasks if _is_complete(task)]
        target_index = min(len(steps) - 1, index + 1)
        if target_index <= index:
            for task in pending:
                if isinstance(task, dict):
                    task["defer_count"] = int(task.get("defer_count", 0) or 0) + 1
                    if task["defer_count"] > MAX_DEFERRALS:
                        task["completion_percent"] = max(
                            0, int(task.get("completion_percent", 0) or 0) - 10
                        )
            schedule["tasks"].extend(pending)
            step.content = json.dumps(schedule, ensure_ascii=False)
            changed = True
            continue
        target = parse_step_content(steps[target_index].content)
        target_tasks = target.get("tasks", [])
        for task in pending:
            if not isinstance(task, dict):
                continue
            task["defer_count"] = int(task.get("defer_count", 0) or 0) + 1
            if task["defer_count"] > MAX_DEFERRALS:
                task["completion_percent"] = max(
                    0, int(task.get("completion_percent", 0) or 0) - 10
                )
            target_tasks.insert(0, task)
        target["tasks"] = sorted(
            target_tasks,
            key=lambda task: 0 if isinstance(task, dict) and task.get("user_priority") else 1,
        )[:DAILY_TASK_LIMIT]
        step.content = json.dumps(schedule, ensure_ascii=False)
        steps[target_index].content = json.dumps(target, ensure_ascii=False)
        changed = True
    return changed


def _task(raw: Any, fallback_title: str) -> dict[str, Any]:
    if isinstance(raw, dict):
        title = str(raw.get("title") or fallback_title).strip()
        subtasks = raw.get("subtasks")
        if not isinstance(subtasks, list):
            subtasks = []
    else:
        title = str(raw or fallback_title).strip()
        subtasks = []
    subtasks = [str(item).strip() for item in subtasks if str(item).strip()][:2]
    while len(subtasks) < 2:
        subtasks.append("Ghi lại kết quả và một lỗi cần sửa.")
    return {
        "task_id": str(raw.get("task_id") or uuid.uuid4()) if isinstance(raw, dict) else str(uuid.uuid4()),
        "title": title[:160],
        "subtasks": subtasks,
        "minutes": 0,
        "completion_percent": int(raw.get("completion_percent", 0) or 0) if isinstance(raw, dict) else 0,
        "defer_count": int(raw.get("defer_count", 0) or 0) if isinstance(raw, dict) else 0,
        "status": str(raw.get("status", "pending")) if isinstance(raw, dict) else "pending",
        "resources": raw.get("resources", []) if isinstance(raw, dict) and isinstance(raw.get("resources"), list) else [],
    }


def _expand_tasks(raw: Any, fallback_title: str) -> list[dict[str, Any]]:
    """Turn nested AI subtasks into independently actionable task records."""
    parent = _task(raw, fallback_title)
    subtasks = parent.pop("subtasks", [])
    if not subtasks:
        return [parent]
    expanded = []
    for index, subtask in enumerate(subtasks, start=1):
        task = dict(parent)
        task["task_id"] = f"{parent['task_id']}-{index}"
        task["title"] = f"{parent['title']}: {subtask}"[:160]
        expanded.append(task)
    return expanded


def normalize_week(
    ai_steps: list[dict[str, Any]],
    goals: list[dict[str, Any]],
    previous_steps: list[dict[str, Any]] | None = None,
    start: date | None = None,
) -> list[dict[str, Any]]:
    start = start or date.today()
    days: list[list[dict[str, Any]]] = [[] for _ in range(7)]

    for index, goal in enumerate(goals):
        if str(goal.get("status", "pending")) == "completed":
            continue
        title = str(goal.get("title") or "Mục tiêu cá nhân").strip()
        note = str(goal.get("note") or "Hoàn thành phần nhỏ nhất có thể kiểm tra được.").strip()
        target = goal.get("target_date")
        day_index = 0
        if isinstance(target, date):
            day_index = max(0, min(6, (target - start).days))
        goal_tasks = _expand_tasks(
            {"title": title, "subtasks": [note, "Đánh dấu phần đã hoàn thành."]},
            title,
        )
        for goal_task in goal_tasks:
            goal_task["user_priority"] = True
            days[day_index].append(goal_task)

    for index, step in enumerate(ai_steps[:7]):
        raw_tasks = step.get("tasks") if isinstance(step, dict) else None
        if not isinstance(raw_tasks, list):
            raw_tasks = [{"title": step.get("content", ""), "subtasks": []}]
        for raw in raw_tasks:
            if len(days[index]) >= DAILY_TASK_LIMIT:
                break
            for generated_task in _expand_tasks(raw, f"Ôn tập ngày {index + 1}"):
                if len(days[index]) >= DAILY_TASK_LIMIT:
                    break
                generated_task["user_priority"] = False
                days[index].append(generated_task)

    if previous_steps:
        for previous in previous_steps:
            content = parse_step_content(previous.get("content", ""))
            previous_date = content.get("date")
            try:
                previous_day = date.fromisoformat(previous_date) if previous_date else start
            except ValueError:
                previous_day = start
            if previous_day >= start:
                continue
            target_index = min(6, max(0, (previous_day - start).days + 1))
            for raw in content.get("tasks", []):
                for task in _expand_tasks(raw, "Nhiệm vụ còn lại"):
                    if task["completion_percent"] >= 100:
                        continue
                    task["defer_count"] = int(raw.get("defer_count", 0)) + 1 if isinstance(raw, dict) else 1
                    if task["defer_count"] > MAX_DEFERRALS:
                        task["completion_percent"] = max(0, int(raw.get("completion_percent", 0)) - 10)
                        continue
                    if len(days[target_index]) < DAILY_TASK_LIMIT:
                        days[target_index].insert(0, task)

    result: list[dict[str, Any]] = []
    for index, tasks in enumerate(days):
        tasks = tasks[:DAILY_TASK_LIMIT]
        available = DAILY_LIMIT_MINUTES
        if tasks:
            minutes = max(1, available // len(tasks))
            for task in tasks:
                task["minutes"] = minutes
        result.append(
            {
                "step_number": index + 1,
                "title": f"Ngày {index + 1} · {start + timedelta(days=index):%d/%m}",
                "content": json.dumps(
                    {
                        "date": (start + timedelta(days=index)).isoformat(),
                        "daily_limit_minutes": DAILY_LIMIT_MINUTES,
                        "max_tasks": DAILY_TASK_LIMIT,
                        "tasks": tasks,
                    },
                    ensure_ascii=False,
                ),
            }
        )
    return result
