from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.shared.runtime.errors import ConfigurationError

from .workflow_runtime_shared import NodeOutcome


class WorkflowChapterSplitGraphState(TypedDict, total=False):
    prompt_bundle: dict[str, Any]
    credential: Any
    raw_output: dict[str, Any]
    budget_error: Exception | None
    chapters: list[Any]
    chapter_payload: dict[str, Any]
    outcome: NodeOutcome


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
        self._graph = self._build_graph()

    async def run(self) -> NodeOutcome:
        final_state = await self._graph.ainvoke({})
        outcome = final_state.get("outcome")
        if outcome is None:
            raise ConfigurationError("Workflow chapter split runtime completed without outcome")
        return outcome

    def _build_graph(self):
        graph = StateGraph(WorkflowChapterSplitGraphState)
        graph.add_node("prepare_request", self._prepare_request)
        graph.add_node("run_before_generate_hook", self._run_before_generate_hook)
        graph.add_node("call_llm", self._call_llm)
        graph.add_node("parse_output", self._parse_output)
        graph.add_node("replace_tasks", self._replace_tasks)
        graph.add_node("append_artifact", self._append_artifact)
        graph.add_node("build_hook_payload", self._build_hook_payload)
        graph.add_node("run_after_generate_hook", self._run_after_generate_hook)
        graph.add_node("record_prompt_replay", self._record_prompt_replay)
        graph.add_node("complete_execution", self._complete_execution)
        graph.add_node("build_outcome", self._build_outcome)
        graph.add_edge(START, "prepare_request")
        graph.add_edge("prepare_request", "run_before_generate_hook")
        graph.add_edge("run_before_generate_hook", "call_llm")
        graph.add_edge("call_llm", "parse_output")
        graph.add_edge("parse_output", "replace_tasks")
        graph.add_edge("replace_tasks", "append_artifact")
        graph.add_edge("append_artifact", "build_hook_payload")
        graph.add_edge("build_hook_payload", "run_after_generate_hook")
        graph.add_edge("run_after_generate_hook", "record_prompt_replay")
        graph.add_edge("record_prompt_replay", "complete_execution")
        graph.add_edge("complete_execution", "build_outcome")
        graph.add_edge("build_outcome", END)
        return graph.compile(name="workflow_chapter_split_runtime")

    async def _prepare_request(
        self,
        _state: WorkflowChapterSplitGraphState,
    ) -> WorkflowChapterSplitGraphState:
        prompt_bundle, credential = await self.prepare_request()
        return {
            "prompt_bundle": prompt_bundle,
            "credential": credential,
        }

    async def _run_before_generate_hook(
        self,
        _state: WorkflowChapterSplitGraphState,
    ) -> WorkflowChapterSplitGraphState:
        await self.run_before_generate_hook()
        return {}

    async def _call_llm(
        self,
        state: WorkflowChapterSplitGraphState,
    ) -> WorkflowChapterSplitGraphState:
        prompt_bundle = state.get("prompt_bundle")
        if prompt_bundle is None:
            raise ConfigurationError("Workflow chapter split runtime missing prompt bundle")
        raw_output, budget_error = await self.call_llm(prompt_bundle, state.get("credential"))
        return {
            "raw_output": raw_output,
            "budget_error": budget_error,
        }

    def _parse_output(
        self,
        state: WorkflowChapterSplitGraphState,
    ) -> WorkflowChapterSplitGraphState:
        raw_output = state.get("raw_output")
        if raw_output is None:
            raise ConfigurationError("Workflow chapter split runtime missing raw output")
        budget_error = state.get("budget_error")
        chapters = self.parse_chapters(raw_output["content"])
        if budget_error is not None:
            self.ensure_budget_action_supported(budget_error)
        return {"chapters": chapters}

    async def _replace_tasks(
        self,
        state: WorkflowChapterSplitGraphState,
    ) -> WorkflowChapterSplitGraphState:
        chapters = state.get("chapters")
        if chapters is None:
            raise ConfigurationError("Workflow chapter split runtime missing chapters")
        await self.replace_chapter_tasks(chapters)
        return {}

    def _append_artifact(
        self,
        state: WorkflowChapterSplitGraphState,
    ) -> WorkflowChapterSplitGraphState:
        chapters = state.get("chapters")
        if chapters is None:
            raise ConfigurationError("Workflow chapter split runtime missing chapters for artifact")
        self.append_artifact(chapters)
        return {}

    def _build_hook_payload(
        self,
        state: WorkflowChapterSplitGraphState,
    ) -> WorkflowChapterSplitGraphState:
        chapters = state.get("chapters")
        if chapters is None:
            raise ConfigurationError("Workflow chapter split runtime missing chapters for hook payload")
        return {
            "chapter_payload": self.build_hook_payload(
                chapters,
                state.get("budget_error"),
            )
        }

    async def _run_after_generate_hook(
        self,
        state: WorkflowChapterSplitGraphState,
    ) -> WorkflowChapterSplitGraphState:
        chapter_payload = state.get("chapter_payload")
        if chapter_payload is None:
            raise ConfigurationError("Workflow chapter split runtime missing after_generate payload")
        await self.run_after_generate_hook(chapter_payload)
        return {}

    def _record_prompt_replay(
        self,
        state: WorkflowChapterSplitGraphState,
    ) -> WorkflowChapterSplitGraphState:
        prompt_bundle = state.get("prompt_bundle")
        raw_output = state.get("raw_output")
        if prompt_bundle is None or raw_output is None:
            raise ConfigurationError("Workflow chapter split runtime missing prompt replay state")
        self.record_prompt_replay(prompt_bundle, raw_output)
        return {}

    def _complete_execution(
        self,
        state: WorkflowChapterSplitGraphState,
    ) -> WorkflowChapterSplitGraphState:
        chapters = state.get("chapters")
        if chapters is None:
            raise ConfigurationError("Workflow chapter split runtime missing chapters for completion")
        self.complete_execution(len(chapters))
        return {}

    def _build_outcome(
        self,
        state: WorkflowChapterSplitGraphState,
    ) -> WorkflowChapterSplitGraphState:
        chapter_payload = state.get("chapter_payload")
        if chapter_payload is None:
            raise ConfigurationError("Workflow chapter split runtime missing outcome payload")
        return {
            "outcome": self.build_outcome(
                state.get("budget_error"),
                chapter_payload,
            )
        }
