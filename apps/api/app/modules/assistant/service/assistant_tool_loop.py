from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
import json
from typing import Any, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.provider_interop_stream_support import StreamInterruptedError

from .assistant_tool_exposure_policy import AssistantToolExposurePolicy
from .assistant_tool_executor import AssistantToolExecutor
from .assistant_tool_runtime_dto import (
    AssistantToolExecutionContext,
    AssistantToolExposureContext,
    AssistantToolResultEnvelope,
)

if TYPE_CHECKING:
    from .assistant_turn_runtime_support import AssistantTurnContext


ToolModelCaller = Callable[..., Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class AssistantToolLoopResult:
    raw_output: dict[str, Any]


@dataclass(frozen=True)
class AssistantToolLoopIterationItem:
    event_name: str | None = None
    event_payload: dict[str, Any] | None = None
    raw_output: dict[str, Any] | None = None


@dataclass
class _UsageTotals:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class AssistantToolLoop:
    def __init__(
        self,
        *,
        exposure_policy: AssistantToolExposurePolicy,
        executor: AssistantToolExecutor,
    ) -> None:
        self.exposure_policy = exposure_policy
        self.executor = executor

    async def execute(
        self,
        db: AsyncSession,
        *,
        turn_context: "AssistantTurnContext",
        owner_id: Any,
        project_id: Any,
        prompt: str,
        system_prompt: str | None,
        model_caller: ToolModelCaller,
        should_stop: Callable[[], Awaitable[bool]] | None = None,
    ) -> AssistantToolLoopResult:
        async for item in self.iterate(
            db,
            turn_context=turn_context,
            owner_id=owner_id,
            project_id=project_id,
            prompt=prompt,
            system_prompt=system_prompt,
            model_caller=model_caller,
            should_stop=should_stop,
        ):
            if item.raw_output is not None:
                return AssistantToolLoopResult(raw_output=item.raw_output)
        raise ConfigurationError("Assistant tool loop exited without final output")

    def resolve_tool_schemas(
        self,
        *,
        turn_context: "AssistantTurnContext",
        project_id: Any,
    ) -> list[dict[str, Any]]:
        visible_tools = self.exposure_policy.resolve_visible_tools(
            context=AssistantToolExposureContext(
                project_id=project_id,
                requested_write_scope=turn_context.requested_write_scope,
            )
        )
        return [_serialize_tool_schema(item) for item in visible_tools]

    async def iterate(
        self,
        db: AsyncSession,
        *,
        turn_context: "AssistantTurnContext",
        owner_id: Any,
        project_id: Any,
        prompt: str,
        system_prompt: str | None,
        model_caller: ToolModelCaller,
        initial_raw_output: dict[str, Any] | None = None,
        should_stop: Callable[[], Awaitable[bool]] | None = None,
    ) -> AsyncIterator[AssistantToolLoopIterationItem]:
        tool_schemas = self.resolve_tool_schemas(
            turn_context=turn_context,
            project_id=project_id,
        )
        if not tool_schemas:
            await _raise_if_cancelled(should_stop)
            yield AssistantToolLoopIterationItem(
                raw_output=initial_raw_output
                or await model_caller(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    tools=[],
                )
            )
            return
        usage = _UsageTotals()
        output_items: list[dict[str, Any]] = []
        prompt_parts = [prompt]
        pending_output = initial_raw_output
        while True:
            await _raise_if_cancelled(should_stop)
            if pending_output is None:
                pending_output = await model_caller(
                    prompt="\n\n".join(part for part in prompt_parts if part.strip()),
                    system_prompt=system_prompt,
                    tools=tool_schemas,
                )
            raw_output = pending_output
            pending_output = None
            _merge_usage_totals(usage, raw_output)
            tool_calls = _read_tool_calls(raw_output)
            if not tool_calls:
                yield AssistantToolLoopIterationItem(
                    raw_output=_build_final_output(
                        turn_context=turn_context,
                        raw_output=raw_output,
                        usage=usage,
                        output_items=output_items,
                    )
                )
                return
            _append_intermediate_text_item(output_items, turn_context, raw_output)
            tool_results: list[AssistantToolResultEnvelope] = []
            for tool_call in tool_calls:
                await _raise_if_cancelled(should_stop)
                yield AssistantToolLoopIterationItem(
                    event_name="tool_call_start",
                    event_payload=_build_tool_call_start_payload(tool_call),
                )
                tool_result = await self._execute_single_tool_call(
                    db,
                    owner_id=owner_id,
                    project_id=project_id,
                    tool_call=tool_call,
                )
                tool_results.append(tool_result)
                yield AssistantToolLoopIterationItem(
                    event_name="tool_call_result",
                    event_payload=_build_tool_call_result_payload(tool_call, tool_result),
                )
            output_items.extend(
                _build_tool_cycle_output_items(
                    turn_context=turn_context,
                    start_index=len(output_items),
                    tool_calls=tool_calls,
                    tool_results=tool_results,
                )
            )
            prompt_parts.append(_render_tool_cycle_projection(raw_output, tool_calls, tool_results))

    async def _execute_single_tool_call(
        self,
        db: AsyncSession,
        *,
        owner_id: Any,
        project_id: Any,
        tool_call: dict[str, Any],
    ) -> AssistantToolResultEnvelope:
        arguments = tool_call.get("arguments")
        if not isinstance(arguments, dict):
            raise ConfigurationError("Tool call arguments must decode to an object")
        return await self.executor.execute(
            db,
            AssistantToolExecutionContext(
                owner_id=owner_id,
                project_id=project_id,
                arguments=arguments,
                tool_call_id=str(tool_call["tool_call_id"]),
                tool_name=str(tool_call["tool_name"]),
                execution_locus="local_runtime",
            ),
        )


def _serialize_tool_schema(descriptor: Any) -> dict[str, Any]:
    return {
        "name": descriptor.name,
        "description": descriptor.description,
        "parameters": descriptor.input_schema,
    }


def _read_tool_calls(raw_output: dict[str, Any]) -> list[dict[str, Any]]:
    tool_calls = raw_output.get("tool_calls")
    if tool_calls is None:
        return []
    if not isinstance(tool_calls, list):
        raise ConfigurationError("LLM tool_calls must be an array")
    normalized: list[dict[str, Any]] = []
    for item in tool_calls:
        if not isinstance(item, dict):
            raise ConfigurationError("LLM tool_calls entries must be objects")
        tool_call_id = item.get("tool_call_id")
        tool_name = item.get("tool_name")
        if not isinstance(tool_call_id, str) or not tool_call_id.strip():
            raise ConfigurationError("LLM tool_call_id must be a non-empty string")
        if not isinstance(tool_name, str) or not tool_name.strip():
            raise ConfigurationError("LLM tool_name must be a non-empty string")
        normalized.append(
            {
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "arguments": item.get("arguments"),
                "arguments_text": item.get("arguments_text"),
                "provider_ref": item.get("provider_ref"),
            }
        )
    return normalized


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
        items.append(
            {
                "item_type": "tool_call",
                "item_id": f"{turn_context.run_id}:tool_call:{current_index}",
                "status": "completed",
                "provider_ref": tool_call.get("provider_ref"),
                "call_id": tool_call["tool_call_id"],
                "payload": {
                    "tool_name": tool_call["tool_name"],
                    "arguments": tool_call.get("arguments"),
                    "arguments_text": tool_call.get("arguments_text"),
                },
            }
        )
        current_index += 1
        items.append(
            {
                "item_type": "tool_result",
                "item_id": f"{turn_context.run_id}:tool_result:{current_index}",
                "status": tool_result.status,
                "call_id": tool_result.tool_call_id,
                "payload": {
                    "structured_output": tool_result.structured_output,
                    "content_items": tool_result.content_items,
                    "resource_links": tool_result.resource_links,
                    "error": tool_result.error,
                },
            }
        )
        current_index += 1
    return items


def _build_final_output(
    *,
    turn_context: "AssistantTurnContext",
    raw_output: dict[str, Any],
    usage: _UsageTotals,
    output_items: list[dict[str, Any]],
) -> dict[str, Any]:
    final_output = dict(raw_output)
    final_output["input_tokens"] = usage.input_tokens or raw_output.get("input_tokens")
    final_output["output_tokens"] = usage.output_tokens or raw_output.get("output_tokens")
    final_output["total_tokens"] = usage.total_tokens or raw_output.get("total_tokens")
    final_output["output_items"] = [
        *output_items,
        _build_text_output_item(
            turn_context=turn_context,
            item_index=len(output_items),
            raw_output=raw_output,
        ),
    ]
    return final_output


def _build_tool_call_start_payload(tool_call: dict[str, Any]) -> dict[str, Any]:
    return {
        "tool_call_id": tool_call["tool_call_id"],
        "tool_name": tool_call["tool_name"],
        "target_summary": _build_tool_target_summary(tool_call),
        "arguments": tool_call.get("arguments"),
        "arguments_text": tool_call.get("arguments_text"),
    }


def _build_tool_call_result_payload(
    tool_call: dict[str, Any],
    tool_result: AssistantToolResultEnvelope,
) -> dict[str, Any]:
    return {
        "tool_call_id": tool_call["tool_call_id"],
        "tool_name": tool_call["tool_name"],
        "status": tool_result.status,
        "result_summary": _build_tool_result_summary(tool_result),
        "resource_links": tool_result.resource_links,
        "error": tool_result.error,
    }


def _render_tool_cycle_projection(
    raw_output: dict[str, Any],
    tool_calls: list[dict[str, Any]],
    tool_results: list[AssistantToolResultEnvelope],
) -> str:
    sections: list[str] = []
    assistant_text = raw_output.get("content")
    if isinstance(assistant_text, str) and assistant_text.strip():
        sections.append(f"【上一轮助手输出】\n{assistant_text.strip()}")
    for tool_call, tool_result in zip(tool_calls, tool_results, strict=True):
        sections.append(
            "\n".join(
                [
                    "【工具调用】",
                    f"名称：{tool_call['tool_name']}",
                    f"调用 ID：{tool_call['tool_call_id']}",
                    f"参数：{_dump_json(tool_call.get('arguments'))}",
                ]
            )
        )
        sections.append(
            "\n".join(
                [
                    "【工具结果】",
                    f"状态：{tool_result.status}",
                    _render_tool_result_content(tool_result),
                ]
            ).strip()
        )
    return "\n\n".join(section for section in sections if section.strip())


def _render_tool_result_content(result: AssistantToolResultEnvelope) -> str:
    if result.content_items:
        lines: list[str] = []
        for item in result.content_items:
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                lines.append(text.strip())
        if lines:
            return "\n\n".join(lines)
    return _dump_json(result.structured_output)


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


def _merge_usage_totals(totals: _UsageTotals, raw_output: dict[str, Any]) -> None:
    totals.input_tokens += _read_usage_value(raw_output.get("input_tokens"))
    totals.output_tokens += _read_usage_value(raw_output.get("output_tokens"))
    totals.total_tokens += _read_usage_value(raw_output.get("total_tokens"))


def _read_usage_value(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return value


def _dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _build_tool_target_summary(tool_call: dict[str, Any]) -> dict[str, Any]:
    arguments = tool_call.get("arguments")
    if not isinstance(arguments, dict):
        return {}
    paths = arguments.get("paths")
    summary: dict[str, Any] = {}
    if isinstance(paths, list):
        normalized_paths = [item for item in paths if isinstance(item, str) and item.strip()]
        if normalized_paths:
            summary["paths"] = normalized_paths
            summary["document_count"] = len(normalized_paths)
    cursors = arguments.get("cursors")
    if isinstance(cursors, list):
        summary["cursor_count"] = len([item for item in cursors if isinstance(item, str) and item.strip()])
    return summary


def _build_tool_result_summary(result: AssistantToolResultEnvelope) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "resource_count": len(result.resource_links),
        "content_item_count": len(result.content_items),
    }
    paths = [
        item["path"]
        for item in result.resource_links
        if isinstance(item, dict) and isinstance(item.get("path"), str) and item["path"].strip()
    ]
    if paths:
        summary["paths"] = paths
        summary["document_count"] = len(paths)
    if result.error is not None:
        summary["error_code"] = result.error.get("code")
    return summary


async def _raise_if_cancelled(should_stop: Callable[[], Awaitable[bool]] | None) -> None:
    if should_stop is None:
        return
    if await should_stop():
        raise StreamInterruptedError()
