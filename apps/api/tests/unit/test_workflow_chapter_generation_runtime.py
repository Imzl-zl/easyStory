import pytest

from app.modules.workflow.service.workflow_chapter_generation_runtime import (
    WorkflowChapterGenerationRuntime,
)
from app.modules.workflow.service.workflow_runtime_shared import NodeOutcome, ReviewCycleOutcome


async def _return_async(value):
    return value


@pytest.mark.asyncio
async def test_workflow_chapter_generation_runtime_runs_success_path() -> None:
    call_log: list[object] = []
    review_outcome = ReviewCycleOutcome("passed", "正文", "generated")
    candidate = ("content-1", "version-1", 1234)
    outcome = NodeOutcome(next_node_id="chapter_gen")

    runtime = WorkflowChapterGenerationRuntime(
        generate_chapter=lambda: _return_async(
            (
                {"context_snapshot_hash": "hash-1"},
                object(),
                {"content": "原始输出"},
                "生成正文",
                None,
            )
        ),
        record_prompt_replay=lambda prompt_bundle, raw_output: call_log.append(
            ("replay", prompt_bundle, raw_output)
        ),
        resolve_review_outcome=lambda generated_content, prompt_bundle, generation_budget_error: _return_async(
            call_log.append(
                ("review", generated_content, prompt_bundle, generation_budget_error)
            )
            or review_outcome
        ),
        persist_candidate=lambda context_snapshot_hash, resolved_review_outcome: _return_async(
            call_log.append(("candidate", context_snapshot_hash, resolved_review_outcome))
            or candidate
        ),
        build_hook_payload=lambda resolved_review_outcome, resolved_candidate, generated_content: (
            call_log.append(
                ("hook_payload", resolved_review_outcome, resolved_candidate, generated_content)
            )
            or {"chapter": {"number": 1}}
        ),
        run_after_generate_hook=lambda hook_payload: _return_async(
            call_log.append(("after_generate", hook_payload))
        ),
        finalize_execution=lambda resolved_review_outcome, resolved_candidate, hook_payload: (
            call_log.append(
                ("finalize", resolved_review_outcome, resolved_candidate, hook_payload)
            )
            or outcome
        ),
    )

    result = await runtime.run()

    assert result == outcome
    assert call_log == [
        ("replay", {"context_snapshot_hash": "hash-1"}, {"content": "原始输出"}),
        ("review", "生成正文", {"context_snapshot_hash": "hash-1"}, None),
        ("candidate", "hash-1", review_outcome),
        ("hook_payload", review_outcome, candidate, "生成正文"),
        ("after_generate", {"chapter": {"number": 1}}),
        ("finalize", review_outcome, candidate, {"chapter": {"number": 1}}),
    ]


@pytest.mark.asyncio
async def test_workflow_chapter_generation_runtime_skips_after_generate_without_candidate() -> None:
    call_log: list[object] = []
    review_outcome = ReviewCycleOutcome("skip", "正文", "generated", failure_message="跳过")
    candidate = (None, None, None)
    outcome = NodeOutcome(next_node_id="chapter_gen")

    runtime = WorkflowChapterGenerationRuntime(
        generate_chapter=lambda: _return_async(
            (
                {"context_snapshot_hash": "hash-1"},
                object(),
                {"content": "原始输出"},
                "生成正文",
                None,
            )
        ),
        record_prompt_replay=lambda prompt_bundle, raw_output: call_log.append(
            ("replay", prompt_bundle, raw_output)
        ),
        resolve_review_outcome=lambda generated_content, prompt_bundle, generation_budget_error: _return_async(
            review_outcome
        ),
        persist_candidate=lambda context_snapshot_hash, resolved_review_outcome: _return_async(candidate),
        build_hook_payload=lambda resolved_review_outcome, resolved_candidate, generated_content: (
            call_log.append(("hook_payload", resolved_candidate)) or {"review": {"resolution": "skip"}}
        ),
        run_after_generate_hook=lambda hook_payload: _return_async(
            call_log.append(("after_generate", hook_payload))
        ),
        finalize_execution=lambda resolved_review_outcome, resolved_candidate, hook_payload: (
            call_log.append(("finalize", resolved_candidate, hook_payload)) or outcome
        ),
    )

    result = await runtime.run()

    assert result == outcome
    assert ("after_generate", {"review": {"resolution": "skip"}}) not in call_log
    assert call_log == [
        ("replay", {"context_snapshot_hash": "hash-1"}, {"content": "原始输出"}),
        ("hook_payload", candidate),
        ("finalize", candidate, {"review": {"resolution": "skip"}}),
    ]
