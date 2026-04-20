from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.shared.runtime.errors import ConfigurationError

from .workflow_runtime_shared import NodeOutcome, ReviewCycleOutcome


class WorkflowChapterGenerationGraphState(TypedDict, total=False):
    prompt_bundle: dict[str, Any]
    raw_output: dict[str, Any]
    generated_content: str
    generation_budget_error: Exception | None
    review_outcome: ReviewCycleOutcome
    candidate: tuple[str | None, str | None, int | None]
    hook_payload: dict[str, Any]
    outcome: NodeOutcome


class LangGraphWorkflowChapterGenerationRuntime:
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
        self._graph = self._build_graph()

    async def run(self) -> NodeOutcome:
        final_state = await self._graph.ainvoke({})
        outcome = final_state.get("outcome")
        if outcome is None:
            raise ConfigurationError("Workflow chapter generation runtime completed without outcome")
        return outcome

    def _build_graph(self):
        graph = StateGraph(WorkflowChapterGenerationGraphState)
        graph.add_node("generate_chapter", self._generate_chapter)
        graph.add_node("record_prompt_replay", self._record_prompt_replay)
        graph.add_node("resolve_review_outcome", self._resolve_review_outcome)
        graph.add_node("persist_candidate", self._persist_candidate)
        graph.add_node("build_hook_payload", self._build_hook_payload)
        graph.add_node("run_after_generate_hook", self._run_after_generate_hook)
        graph.add_node("finalize_execution", self._finalize_execution)
        graph.add_edge(START, "generate_chapter")
        graph.add_edge("generate_chapter", "record_prompt_replay")
        graph.add_edge("record_prompt_replay", "resolve_review_outcome")
        graph.add_edge("resolve_review_outcome", "persist_candidate")
        graph.add_edge("persist_candidate", "build_hook_payload")
        graph.add_conditional_edges(
            "build_hook_payload",
            self._route_after_hook_payload,
            {
                "run_after_generate_hook": "run_after_generate_hook",
                "finalize_execution": "finalize_execution",
            },
        )
        graph.add_edge("run_after_generate_hook", "finalize_execution")
        graph.add_edge("finalize_execution", END)
        return graph.compile(name="workflow_chapter_generation_runtime")

    async def _generate_chapter(
        self,
        _state: WorkflowChapterGenerationGraphState,
    ) -> WorkflowChapterGenerationGraphState:
        prompt_bundle, _credential, raw_output, generated_content, generation_budget_error = (
            await self.generate_chapter()
        )
        return {
            "prompt_bundle": prompt_bundle,
            "raw_output": raw_output,
            "generated_content": generated_content,
            "generation_budget_error": generation_budget_error,
        }

    def _record_prompt_replay(
        self,
        state: WorkflowChapterGenerationGraphState,
    ) -> WorkflowChapterGenerationGraphState:
        prompt_bundle = state.get("prompt_bundle")
        raw_output = state.get("raw_output")
        if prompt_bundle is None or raw_output is None:
            raise ConfigurationError("Workflow chapter generation runtime missing prompt replay state")
        self.record_prompt_replay(prompt_bundle, raw_output)
        return {}

    async def _resolve_review_outcome(
        self,
        state: WorkflowChapterGenerationGraphState,
    ) -> WorkflowChapterGenerationGraphState:
        prompt_bundle = state.get("prompt_bundle")
        generated_content = state.get("generated_content")
        if prompt_bundle is None or generated_content is None:
            raise ConfigurationError("Workflow chapter generation runtime missing review state")
        return {
            "review_outcome": await self.resolve_review_outcome(
                generated_content,
                prompt_bundle,
                state.get("generation_budget_error"),
            )
        }

    async def _persist_candidate(
        self,
        state: WorkflowChapterGenerationGraphState,
    ) -> WorkflowChapterGenerationGraphState:
        prompt_bundle = state.get("prompt_bundle")
        review_outcome = state.get("review_outcome")
        if prompt_bundle is None or review_outcome is None:
            raise ConfigurationError("Workflow chapter generation runtime missing candidate state")
        return {
            "candidate": await self.persist_candidate(
                prompt_bundle["context_snapshot_hash"],
                review_outcome,
            )
        }

    def _build_hook_payload(
        self,
        state: WorkflowChapterGenerationGraphState,
    ) -> WorkflowChapterGenerationGraphState:
        review_outcome = state.get("review_outcome")
        candidate = state.get("candidate")
        generated_content = state.get("generated_content")
        if review_outcome is None or candidate is None or generated_content is None:
            raise ConfigurationError("Workflow chapter generation runtime missing hook payload state")
        return {
            "hook_payload": self.build_hook_payload(
                review_outcome,
                candidate,
                generated_content,
            )
        }

    def _route_after_hook_payload(self, state: WorkflowChapterGenerationGraphState) -> str:
        candidate = state.get("candidate")
        if candidate is None:
            raise ConfigurationError("Workflow chapter generation runtime missing candidate")
        if candidate[0] is not None:
            return "run_after_generate_hook"
        return "finalize_execution"

    async def _run_after_generate_hook(
        self,
        state: WorkflowChapterGenerationGraphState,
    ) -> WorkflowChapterGenerationGraphState:
        hook_payload = state.get("hook_payload")
        if hook_payload is None:
            raise ConfigurationError("Workflow chapter generation runtime missing after_generate payload")
        await self.run_after_generate_hook(hook_payload)
        return {}

    def _finalize_execution(
        self,
        state: WorkflowChapterGenerationGraphState,
    ) -> WorkflowChapterGenerationGraphState:
        review_outcome = state.get("review_outcome")
        candidate = state.get("candidate")
        hook_payload = state.get("hook_payload")
        if review_outcome is None or candidate is None or hook_payload is None:
            raise ConfigurationError("Workflow chapter generation runtime missing finalize state")
        return {
            "outcome": self.finalize_execution(
                review_outcome,
                candidate,
                hook_payload,
            )
        }
