import pytest

from app.shared.runtime.errors import BudgetExceededError
from app.modules.workflow.service.workflow_chapter_split_runtime import (
    LangGraphWorkflowChapterSplitRuntime,
)
from app.modules.workflow.service.workflow_runtime_shared import NodeOutcome


async def _return_async(value):
    return value


@pytest.mark.asyncio
async def test_workflow_chapter_split_runtime_runs_success_path() -> None:
    call_log: list[object] = []
    chapters = [type("Chapter", (), {"model_dump": lambda self: {"chapter_number": 1}})()]
    outcome = NodeOutcome(next_node_id="chapter_gen")

    runtime = LangGraphWorkflowChapterSplitRuntime(
        prepare_request=lambda: _return_async(({"input_data": {}, "context_snapshot_hash": "x"}, object())),
        run_before_generate_hook=lambda: _return_async(call_log.append("before")),
        call_llm=lambda prompt_bundle, credential: _return_async(({"content": "{}"}, None)),
        parse_chapters=lambda content: call_log.append(("parse", content)) or chapters,
        ensure_budget_action_supported=lambda budget_error: call_log.append(("budget", budget_error)),
        replace_chapter_tasks=lambda resolved_chapters: _return_async(
            call_log.append(("replace", resolved_chapters))
        ),
        append_artifact=lambda resolved_chapters: call_log.append(("artifact", resolved_chapters)),
        build_hook_payload=lambda resolved_chapters, budget_error: call_log.append(
            ("hook_payload", resolved_chapters, budget_error)
        )
        or {"chapters_count": 1},
        run_after_generate_hook=lambda payload: _return_async(call_log.append(("after", payload))),
        record_prompt_replay=lambda prompt_bundle, raw_output: call_log.append(
            ("replay", prompt_bundle, raw_output)
        ),
        complete_execution=lambda chapters_count: call_log.append(("complete", chapters_count)),
        build_outcome=lambda budget_error, hook_payload: call_log.append(
            ("outcome", budget_error, hook_payload)
        )
        or outcome,
    )

    result = await runtime.run()

    assert result == outcome
    assert call_log == [
        "before",
        ("parse", "{}"),
        ("replace", chapters),
        ("artifact", chapters),
        ("hook_payload", chapters, None),
        ("after", {"chapters_count": 1}),
        ("replay", {"input_data": {}, "context_snapshot_hash": "x"}, {"content": "{}"}),
        ("complete", 1),
        ("outcome", None, {"chapters_count": 1}),
    ]


@pytest.mark.asyncio
async def test_workflow_chapter_split_runtime_propagates_budget_pause() -> None:
    call_log: list[object] = []
    chapters = [type("Chapter", (), {"model_dump": lambda self: {"chapter_number": 1}})()]
    budget_error = BudgetExceededError(
        message="budget",
        action="pause",
        scope="workflow",
        used_tokens=100,
        limit_tokens=10,
        usage_type="generate",
        raw_output={"content": "{}"},
    )
    outcome = NodeOutcome(next_node_id="chapter_gen", pause_reason="budget_exceeded")

    runtime = LangGraphWorkflowChapterSplitRuntime(
        prepare_request=lambda: _return_async(({"input_data": {}}, object())),
        run_before_generate_hook=lambda: _return_async(None),
        call_llm=lambda prompt_bundle, credential: _return_async(({"content": "{}"}, budget_error)),
        parse_chapters=lambda content: chapters,
        ensure_budget_action_supported=lambda resolved_budget_error: call_log.append(
            ("budget", resolved_budget_error)
        ),
        replace_chapter_tasks=lambda resolved_chapters: _return_async(None),
        append_artifact=lambda resolved_chapters: None,
        build_hook_payload=lambda resolved_chapters, resolved_budget_error: {"budget_exceeded": True},
        run_after_generate_hook=lambda payload: _return_async(None),
        record_prompt_replay=lambda prompt_bundle, raw_output: None,
        complete_execution=lambda chapters_count: None,
        build_outcome=lambda resolved_budget_error, hook_payload: call_log.append(
            ("outcome", resolved_budget_error, hook_payload)
        )
        or outcome,
    )

    result = await runtime.run()

    assert result == outcome
    assert call_log == [
        ("budget", budget_error),
        ("outcome", budget_error, {"budget_exceeded": True}),
    ]
