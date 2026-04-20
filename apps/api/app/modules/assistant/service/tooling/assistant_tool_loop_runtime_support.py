from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, TYPE_CHECKING

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.interop.provider_interop_stream_support import StreamInterruptedError
from app.shared.runtime.llm.llm_tool_provider import LLMGenerateToolResponse

from ..assistant_runtime_terminal import build_cancel_requested_terminal_error

ToolModelCaller = Callable[..., Awaitable[LLMGenerateToolResponse]]
ToolStreamModelCaller = Callable[..., AsyncIterator[Any]]

if TYPE_CHECKING:
    from .assistant_tool_loop_runtime import AssistantToolLoopIterationItem


def read_tool_calls(raw_output: dict[str, Any]) -> list[dict[str, Any]]:
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
                "arguments": normalize_tool_call_arguments(item),
                "arguments_text": read_optional_tool_call_string(item.get("arguments_text")),
                "arguments_error": read_optional_tool_call_string(item.get("arguments_error")),
                "provider_ref": item.get("provider_ref"),
                "provider_payload": read_optional_record(item.get("provider_payload")),
            }
        )
    return normalized


def normalize_tool_call_arguments(item: dict[str, Any]) -> dict[str, Any]:
    arguments = item.get("arguments")
    if isinstance(arguments, dict):
        return arguments
    return {}


def read_optional_tool_call_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


async def iterate_model_response(
    *,
    prompt: str,
    system_prompt: str | None,
    tools: list[dict[str, Any]],
    continuation_items: tuple[dict[str, Any], ...],
    provider_continuation_state: dict[str, Any] | None,
    model_caller: ToolModelCaller,
    stream_model_caller: ToolStreamModelCaller | None,
) -> AsyncIterator[AssistantToolLoopIterationItem]:
    from .assistant_tool_loop_runtime import AssistantToolLoopIterationItem

    if stream_model_caller is None:
        yield AssistantToolLoopIterationItem(
            raw_output=await model_caller(
                prompt=prompt,
                system_prompt=system_prompt,
                tools=tools,
                continuation_items=list(continuation_items),
                provider_continuation_state=provider_continuation_state,
            )
        )
        return
    streamed_output = False
    raw_output: LLMGenerateToolResponse | None = None
    async for event in stream_model_caller(
        prompt=prompt,
        system_prompt=system_prompt,
        tools=tools,
        continuation_items=list(continuation_items),
        provider_continuation_state=provider_continuation_state,
    ):
        if event.delta:
            streamed_output = True
            yield AssistantToolLoopIterationItem(
                event_name="chunk",
                event_payload={"delta": event.delta},
            )
        if event.raw_output is not None:
            raw_output = event.raw_output
    if raw_output is None:
        raise ConfigurationError("Streaming continuation completed without final output")
    yield AssistantToolLoopIterationItem(
        raw_output=raw_output,
        raw_output_already_streamed=streamed_output,
    )


async def raise_if_cancelled(
    should_stop: Callable[[], Awaitable[bool]] | None,
    *,
    write_effective: bool = False,
) -> None:
    if should_stop is None:
        return
    if await should_stop():
        if write_effective:
            raise build_cancel_requested_terminal_error(write_effective=True)
        raise StreamInterruptedError()


def read_optional_record(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None
