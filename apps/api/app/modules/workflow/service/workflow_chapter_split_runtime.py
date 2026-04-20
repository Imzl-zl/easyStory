from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.shared.runtime.errors import ConfigurationError

from .workflow_runtime_shared import NodeOutcome


class LangGraphWorkflowChapterSplitRuntime:
    def __init__(
        self,
        *,
        prepare_request: Callable[[], Awaitable[tuple[dict, Any]]],
        run_before_generate_hook: Callable[[], Awaitable[None]],
        call_llm: Callable[[dict, Any], Awaitable[tuple[dict, Exception | None]]],
        parse_chapters: Callable[[Any], list[Any]],
        ensure_budget_action_supported: Callable[[Exception], None],
        replace_chapter_tasks: Callable[[list[Any]], Awaitable[None]],
        append_artifact: Callable[[list[Any]], None],
        build_hook_payload: Callable[[list[Any], Exception | None], dict[str, Any]],
        run_after_generate_hook: Callable[[dict[str, Any]], Awaitable[None]],
        record_prompt_replay: Callable[[dict, dict], None],
        complete_execution: Callable[[int], None],
        build_outcome: Callable[[Exception | None, dict[str, Any]], NodeOutcome],
    ) -> None:
        self.prepare_request = prepare_request
        self.run_before_generate_hook = run_before_generate_hook
        self.call_llm = call_llm
        self.parse_chapters = parse_chapters
        self.ensure_budget_action_supported = ensure_budget_action_supported
        self.replace_chapter_tasks = replace_chapter_tasks
        self.append_artifact = append_artifact
        self.build_hook_payload = build_hook_payload
        self.run_after_generate_hook = run_after_generate_hook
        self.record_prompt_replay = record_prompt_replay
        self.complete_execution = complete_execution
        self.build_outcome = build_outcome

    async def run(self) -> NodeOutcome:
        prompt_bundle, credential = await self.prepare_request()
        await self.run_before_generate_hook()
        raw_output, budget_error = await self.call_llm(prompt_bundle, credential)
        chapters = self.parse_chapters(raw_output["content"])
        if budget_error is not None:
            self.ensure_budget_action_supported(budget_error)
        await self.replace_chapter_tasks(chapters)
        self.append_artifact(chapters)
        chapter_payload = self.build_hook_payload(chapters, budget_error)
        await self.run_after_generate_hook(chapter_payload)
        self.record_prompt_replay(prompt_bundle, raw_output)
        self.complete_execution(len(chapters))
        outcome = self.build_outcome(budget_error, chapter_payload)
        if outcome is None:
            raise ConfigurationError("Workflow chapter split runtime completed without outcome")
        return outcome
