from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.llm_protocol_types import (
    LLMContinuationSupport,
    allows_provider_continuation_state,
)

from ..dto import AssistantNormalizedInputItemDTO
from .assistant_tool_runtime_dto import AssistantToolResultEnvelope

if TYPE_CHECKING:
    from ..turn.assistant_turn_runtime_support import AssistantTurnContext


@dataclass
class _UsageTotals:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


def _build_usage_totals_state() -> dict[str, int]:
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
    }


def _append_intermediate_text_item(
    output_items: list[dict[str, Any]],
    turn_context: "AssistantTurnContext",
    raw_output: dict[str, Any],
) -> None:
    content = raw_output.get("content")
    if not isinstance(content, str) or not content.strip():
        return
    provider_ref = raw_output.get("provider_response_id") or raw_output.get("provider")
    output_items.append(
        {
            "item_type": "text",
            "item_id": f"{turn_context.run_id}:text:{len(output_items)}",
            "status": "completed",
            "provider_ref": str(provider_ref) if provider_ref is not None else None,
            "payload": {"content": content, "phase": "pre_tool"},
        }
    )


def _build_tool_cycle_output_items(
    *,
    turn_context: "AssistantTurnContext",
    start_index: int,
    tool_calls: list[dict[str, Any]],
    tool_results: list[AssistantToolResultEnvelope],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    current_index = start_index
    for tool_call, tool_result in zip(tool_calls, tool_results, strict=True):
        tool_call_payload = _build_runtime_tool_call_payload(tool_call)
        items.append(
            {
                "item_type": "tool_call",
                "item_id": f"{turn_context.run_id}:tool_call:{current_index}",
                "status": "completed",
                "provider_ref": tool_call.get("provider_ref"),
                "call_id": tool_call["tool_call_id"],
                "payload": tool_call_payload,
            }
        )
        current_index += 1
        items.append(
            {
                "item_type": "tool_result",
                "item_id": f"{turn_context.run_id}:tool_result:{current_index}",
                "status": tool_result.status,
                "call_id": tool_result.tool_call_id,
                "payload": _build_output_tool_result_payload(tool_call, tool_result),
            }
        )
        current_index += 1
    return items


def _build_tool_cycle_continuation_items(
    *,
    raw_output: dict[str, Any],
    tool_calls: list[dict[str, Any]],
    tool_results: list[AssistantToolResultEnvelope],
    tool_cycle_index: int,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    content = raw_output.get("content")
    if isinstance(content, str) and content.strip():
        items.append(
            {
                "item_type": "message",
                "role": "assistant",
                "content": content.strip(),
            }
        )
    for tool_call, tool_result in zip(tool_calls, tool_results, strict=True):
        tool_call_payload = _build_runtime_tool_call_payload(tool_call)
        tool_call_payload["tool_call_id"] = tool_call["tool_call_id"]
        items.append(
            {
                "item_type": "tool_call",
                "call_id": tool_call["tool_call_id"],
                "tool_cycle_index": tool_cycle_index,
                "payload": tool_call_payload,
            }
        )
        items.append(
            {
                "item_type": "tool_result",
                "status": tool_result.status,
                "call_id": tool_result.tool_call_id,
                "tool_name": tool_call["tool_name"],
                "tool_cycle_index": tool_cycle_index,
                "payload": _build_continuation_tool_result_payload(tool_result),
            }
        )
    return items


def _build_tool_cycle_normalized_input_items(
    *,
    raw_output: dict[str, Any],
    tool_calls: list[dict[str, Any]],
    tool_results: list[AssistantToolResultEnvelope],
) -> list[dict[str, Any]]:
    items: list[AssistantNormalizedInputItemDTO] = []
    content = raw_output.get("content")
    if isinstance(content, str) and content.strip():
        items.append(
            AssistantNormalizedInputItemDTO(
                item_type="message",
                role="assistant",
                content=content.strip(),
                phase="pre_tool",
            )
        )
    for tool_call, tool_result in zip(tool_calls, tool_results, strict=True):
        tool_call_payload = _build_runtime_tool_call_payload(tool_call)
        tool_call_payload["tool_call_id"] = tool_call["tool_call_id"]
        items.append(
            AssistantNormalizedInputItemDTO(
                item_type="tool_call",
                payload=tool_call_payload,
            )
        )
        items.append(
            AssistantNormalizedInputItemDTO(
                item_type="tool_result",
                payload=_build_normalized_input_tool_result_payload(tool_call, tool_result),
            )
        )
    return [item.model_dump(mode="json", exclude_none=True) for item in items]


def _build_runtime_tool_call_payload(tool_call: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "tool_name": tool_call["tool_name"],
        "arguments": tool_call.get("arguments"),
        "arguments_text": tool_call.get("arguments_text"),
    }
    arguments_error = tool_call.get("arguments_error")
    if isinstance(arguments_error, str) and arguments_error.strip():
        payload["arguments_error"] = arguments_error.strip()
    provider_payload = tool_call.get("provider_payload")
    if isinstance(provider_payload, dict):
        payload["provider_payload"] = provider_payload
    return payload


def _build_output_tool_result_payload(
    tool_call: dict[str, Any],
    tool_result: AssistantToolResultEnvelope,
) -> dict[str, Any]:
    payload = {
        "tool_name": tool_call["tool_name"],
        "structured_output": tool_result.structured_output,
        "content_items": tool_result.content_items,
        "resource_links": tool_result.resource_links,
        "error": tool_result.error,
        "audit": tool_result.audit,
    }
    return payload


def _build_normalized_input_tool_result_payload(
    tool_call: dict[str, Any],
    tool_result: AssistantToolResultEnvelope,
) -> dict[str, Any]:
    return {
        "tool_call_id": tool_result.tool_call_id,
        "tool_name": tool_call["tool_name"],
        "status": tool_result.status,
        "structured_output": tool_result.structured_output,
        "content_items": tool_result.content_items,
        "resource_links": tool_result.resource_links,
        "error": tool_result.error,
        "audit": tool_result.audit,
    }


def _build_continuation_tool_result_payload(
    tool_result: AssistantToolResultEnvelope,
) -> dict[str, Any]:
    return {
        "structured_output": tool_result.structured_output,
        "content_items": tool_result.content_items,
        "resource_links": tool_result.resource_links,
        "error": tool_result.error,
    }


def _build_final_response_normalized_input_items(
    raw_output: dict[str, Any],
) -> list[dict[str, Any]]:
    content = raw_output.get("content")
    if not isinstance(content, str) or not content.strip():
        return []
    item = AssistantNormalizedInputItemDTO(
        item_type="message",
        role="assistant",
        content=content.strip(),
        phase="final",
    )
    return [item.model_dump(mode="json", exclude_none=True)]


def _resolve_provider_continuation_state(
    *,
    raw_output: dict[str, Any],
    latest_items: list[dict[str, Any]],
    continuation_support: LLMContinuationSupport,
) -> dict[str, Any] | None:
    if not allows_provider_continuation_state(continuation_support):
        return None
    previous_response_id = raw_output.get("provider_response_id")
    if not isinstance(previous_response_id, str) or not previous_response_id.strip():
        return None
    return {
        "previous_response_id": previous_response_id.strip(),
        "latest_items": latest_items,
    }


def _build_final_output(
    *,
    turn_context: "AssistantTurnContext",
    raw_output: dict[str, Any],
    usage: _UsageTotals | dict[str, int],
    output_items: list[dict[str, Any]],
) -> dict[str, Any]:
    final_output = dict(raw_output)
    final_output["input_tokens"] = _read_usage_total(usage, "input_tokens") or raw_output.get(
        "input_tokens"
    )
    final_output["output_tokens"] = _read_usage_total(usage, "output_tokens") or raw_output.get(
        "output_tokens"
    )
    final_output["total_tokens"] = _read_usage_total(usage, "total_tokens") or raw_output.get(
        "total_tokens"
    )
    final_output["output_items"] = _merge_final_output_items(
        turn_context=turn_context,
        raw_output=raw_output,
        output_items=output_items,
    )
    return final_output


def _merge_usage_totals(totals: _UsageTotals, raw_output: dict[str, Any]) -> None:
    totals.input_tokens += _read_usage_value(raw_output.get("input_tokens"))
    totals.output_tokens += _read_usage_value(raw_output.get("output_tokens"))
    totals.total_tokens += _read_usage_value(raw_output.get("total_tokens"))


def _merge_usage_totals_state(
    totals: dict[str, int],
    raw_output: dict[str, Any],
) -> dict[str, int]:
    return {
        "input_tokens": totals.get("input_tokens", 0) + _read_usage_value(raw_output.get("input_tokens")),
        "output_tokens": totals.get("output_tokens", 0) + _read_usage_value(raw_output.get("output_tokens")),
        "total_tokens": totals.get("total_tokens", 0) + _read_usage_value(raw_output.get("total_tokens")),
    }


def _merge_final_output_items(
    *,
    turn_context: "AssistantTurnContext",
    raw_output: dict[str, Any],
    output_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    provider_output_items = raw_output.get("output_items")
    if isinstance(provider_output_items, list) and provider_output_items:
        return [*output_items, *provider_output_items]
    return [
        *output_items,
        _build_text_output_item(
            turn_context=turn_context,
            item_index=len(output_items),
            raw_output=raw_output,
        ),
    ]


def _build_text_output_item(
    *,
    turn_context: "AssistantTurnContext",
    item_index: int,
    raw_output: dict[str, Any],
) -> dict[str, Any]:
    content = raw_output.get("content")
    if not isinstance(content, str):
        raise ConfigurationError("Assistant output must be plain text")
    provider_ref = raw_output.get("provider_response_id") or raw_output.get("provider")
    return {
        "item_type": "text",
        "item_id": f"{turn_context.run_id}:text:{item_index}",
        "status": "completed",
        "provider_ref": str(provider_ref) if provider_ref is not None else None,
        "payload": {"content": content, "phase": "final"},
    }


def _read_usage_value(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return value


def _read_usage_total(usage: _UsageTotals | dict[str, int], field_name: str) -> int:
    if isinstance(usage, dict):
        return _read_usage_value(usage.get(field_name))
    return _read_usage_value(getattr(usage, field_name, None))
