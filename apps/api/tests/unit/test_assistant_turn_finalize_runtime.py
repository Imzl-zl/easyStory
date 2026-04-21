import pytest

from app.modules.assistant.service.turn.assistant_turn_finalize_runtime import (
    AssistantTurnFinalizeRuntime,
)
from app.shared.runtime.errors import ConfigurationError


@pytest.mark.asyncio
async def test_assistant_turn_finalize_runtime_runs_success_path() -> None:
    call_log: list[object] = []
    response = object()

    runtime = AssistantTurnFinalizeRuntime(
        resolve_content=lambda: call_log.append("resolve_content") or "主回复正文",
        build_after_payload=lambda content: call_log.append(("after_payload", content)) or {
            "response": {"content": content}
        },
        run_after_hooks=lambda payload: _return_async(
            call_log.append(("after_hooks", payload)) or ["after-result"]
        ),
        build_response=lambda content, after_results: call_log.append(
            ("build_response", content, after_results)
        )
        or response,
    )

    result = await runtime.run()

    assert result is response
    assert call_log == [
        "resolve_content",
        ("after_payload", "主回复正文"),
        ("after_hooks", {"response": {"content": "主回复正文"}}),
        ("build_response", "主回复正文", ["after-result"]),
    ]


@pytest.mark.asyncio
async def test_assistant_turn_finalize_runtime_requires_response() -> None:
    runtime = AssistantTurnFinalizeRuntime(
        resolve_content=lambda: "主回复正文",
        build_after_payload=lambda content: {"response": {"content": content}},
        run_after_hooks=lambda payload: _return_async([]),
        build_response=lambda content, after_results: None,
    )

    with pytest.raises(
        ConfigurationError,
        match="Assistant turn finalize runtime completed without response",
    ):
        await runtime.run()


async def _return_async(value):
    return value
