from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.shared.runtime.errors import ConfigurationError

from .workflow_runtime_shared import NodeOutcome, ReviewCycleOutcome


class WorkflowChapterGenerationRuntime:
    def __init__(
        self,
        *,
        generate_chapter: Callable[[], Awaitable[tuple[dict, Any, dict, str, Exception | None]]],
        record_prompt_replay: Callable[[dict, dict], None],
        resolve_review_outcome: Callable[[str, dict, Exception | None], Awaitable[ReviewCycleOutcome]],
        persist_candidate: Callable[[str, ReviewCycleOutcome], Awaitable[tuple[str | None, str | None, int | None]]],
        build_hook_payload: Callable[[ReviewCycleOutcome, tuple[str | None, str | None, int | None], str], dict[str, Any]],
        run_after_generate_hook: Callable[[dict[str, Any]], Awaitable[None]],
        finalize_execution: Callable[[ReviewCycleOutcome, tuple[str | None, str | None, int | None], dict[str, Any]], NodeOutcome],
    ) -> None:
        self.generate_chapter = generate_chapter
        self.record_prompt_replay = record_prompt_replay
        self.resolve_review_outcome = resolve_review_outcome
        self.persist_candidate = persist_candidate
        self.build_hook_payload = build_hook_payload
        self.run_after_generate_hook = run_after_generate_hook
        self.finalize_execution = finalize_execution

    async def run(self) -> NodeOutcome:
        prompt_bundle, _credential, raw_output, generated_content, generation_budget_error = (
            await self.generate_chapter()
        )
        self.record_prompt_replay(prompt_bundle, raw_output)
        review_outcome = await self.resolve_review_outcome(
            generated_content,
            prompt_bundle,
            generation_budget_error,
        )
        candidate = await self.persist_candidate(
            prompt_bundle["context_snapshot_hash"],
            review_outcome,
        )
        hook_payload = self.build_hook_payload(
            review_outcome,
            candidate,
            generated_content,
        )
        if candidate[0] is not None:
            await self.run_after_generate_hook(hook_payload)
        outcome = self.finalize_execution(review_outcome, candidate, hook_payload)
        if outcome is None:
            raise ConfigurationError("Workflow chapter generation runtime completed without outcome")
        return outcome


LangGraphWorkflowChapterGenerationRuntime = WorkflowChapterGenerationRuntime
