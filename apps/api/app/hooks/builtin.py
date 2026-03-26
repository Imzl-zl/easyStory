from __future__ import annotations

from typing import Any

from app.shared.runtime.errors import BusinessRuleError

from app.modules.workflow.service.workflow_runtime_hook_support import HookExecutionContext


def auto_save_content(
    context: HookExecutionContext,
    params: dict[str, Any],
) -> dict[str, Any]:
    content_id = _require_string(context.read_path("content.id"), "content.id")
    result = {
        "saved": True,
        "content_id": content_id,
    }
    chapter = context.payload.get("chapter")
    if isinstance(chapter, dict) and isinstance(chapter.get("number"), int):
        result["chapter_number"] = chapter["number"]
    if _should_include_version(params):
        version_id = _require_string(context.read_path("content.version_id"), "content.version_id")
        result["content_version_id"] = version_id
    return result


def _should_include_version(params: dict[str, Any]) -> bool:
    raw = params.get("save_version", False)
    if not isinstance(raw, bool):
        raise BusinessRuleError("auto_save_content.params.save_version 必须是布尔值")
    return raw


def _require_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BusinessRuleError(f"auto_save_content 缺少 {field_name}")
    return value
