from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.modules.review.engine.contracts import AggregatedReviewResult
from app.shared.runtime.errors import BudgetExceededError, ConfigurationError, ModelFallbackExhaustedError

from .workflow_runtime_shared import ReviewCycleOutcome


class WorkflowReviewFixGraphState(TypedDict, total=False):
    review_outcome: ReviewCycleOutcome
    reviewers: Sequence[Any]
    aggregated: AggregatedReviewResult
    current_content: str
    content_source: str
    fix_attempt: int
    max_fix_attempts: int


class WorkflowReviewFixRuntime:
    def __init__(
        self,
        *,
        generated_content: str,
        generation_budget_error: BudgetExceededError | None,
        build_budget_review_outcome: Callable[[BudgetExceededError, str], ReviewCycleOutcome],
        resolve_auto_review_enabled: Callable[[], bool],
        load_reviewers: Callable[[], Sequence[Any]],
        run_review_round: Callable[[str, Sequence[Any], str], Awaitable[AggregatedReviewResult]],
        resolve_auto_fix_enabled: Callable[[], bool],
        run_fix_attempt: Callable[[str, AggregatedReviewResult, int, int], Awaitable[str]],
        resolve_max_fix_attempts: Callable[[], int],
        select_re_reviewers: Callable[[Sequence[Any], AggregatedReviewResult], Sequence[Any]],
        resolve_fix_failure: Callable[[str], ReviewCycleOutcome],
        resolve_model_fallback_review_outcome: Callable[
            [ModelFallbackExhaustedError, str, str],
            ReviewCycleOutcome,
        ],
    ) -> None:
        self.generated_content = generated_content
        self.generation_budget_error = generation_budget_error
        self.build_budget_review_outcome = build_budget_review_outcome
        self.resolve_auto_review_enabled = resolve_auto_review_enabled
        self.load_reviewers = load_reviewers
        self.run_review_round = run_review_round
        self.resolve_auto_fix_enabled = resolve_auto_fix_enabled
        self.run_fix_attempt = run_fix_attempt
        self.resolve_max_fix_attempts = resolve_max_fix_attempts
        self.select_re_reviewers = select_re_reviewers
        self.resolve_fix_failure = resolve_fix_failure
        self.resolve_model_fallback_review_outcome = resolve_model_fallback_review_outcome
        self._graph = self._build_graph()

    async def run(self) -> ReviewCycleOutcome:
        try:
            final_state = await self._graph.ainvoke({})
        except BudgetExceededError as exc:
            return self.build_budget_review_outcome(exc, self.generated_content)
        review_outcome = final_state.get("review_outcome")
        if review_outcome is None:
            raise ConfigurationError("Workflow review/fix runtime completed without review outcome")
        return review_outcome

    def _build_graph(self):
        graph = StateGraph(WorkflowReviewFixGraphState)
        graph.add_node("resolve_initial_outcome", self._resolve_initial_outcome)
        graph.add_node("load_reviewers", self._load_reviewers)
        graph.add_node("run_auto_review_round", self._run_auto_review_round)
        graph.add_node("resolve_auto_review_outcome", self._resolve_auto_review_outcome)
        graph.add_node("run_fix_attempt", self._run_fix_attempt)
        graph.add_node("run_re_review_round", self._run_re_review_round)
        graph.add_node("resolve_re_review_outcome", self._resolve_re_review_outcome)
        graph.add_node("finish", self._finish)
        graph.add_edge(START, "resolve_initial_outcome")
        graph.add_conditional_edges(
            "resolve_initial_outcome",
            self._route_after_initial_outcome,
            {
                "finish": "finish",
                "load_reviewers": "load_reviewers",
            },
        )
        graph.add_edge("load_reviewers", "run_auto_review_round")
        graph.add_edge("run_auto_review_round", "resolve_auto_review_outcome")
        graph.add_conditional_edges(
            "resolve_auto_review_outcome",
            self._route_after_auto_review_outcome,
            {
                "finish": "finish",
                "run_fix_attempt": "run_fix_attempt",
            },
        )
        graph.add_conditional_edges(
            "run_fix_attempt",
            self._route_after_fix_attempt,
            {
                "finish": "finish",
                "run_re_review_round": "run_re_review_round",
            },
        )
        graph.add_edge("run_re_review_round", "resolve_re_review_outcome")
        graph.add_conditional_edges(
            "resolve_re_review_outcome",
            self._route_after_re_review_outcome,
            {
                "finish": "finish",
                "run_fix_attempt": "run_fix_attempt",
            },
        )
        graph.add_edge("finish", END)
        return graph.compile(name="workflow_review_fix_runtime")

    def _resolve_initial_outcome(
        self,
        _state: WorkflowReviewFixGraphState,
    ) -> WorkflowReviewFixGraphState:
        if self.generation_budget_error is not None:
            return {
                "review_outcome": self.build_budget_review_outcome(
                    self.generation_budget_error,
                    self.generated_content,
                )
            }
        if not self.resolve_auto_review_enabled():
            return {"review_outcome": ReviewCycleOutcome("passed", self.generated_content, "generated")}
        return {}

    def _route_after_initial_outcome(self, state: WorkflowReviewFixGraphState) -> str:
        if state.get("review_outcome") is not None:
            return "finish"
        return "load_reviewers"

    def _load_reviewers(
        self,
        _state: WorkflowReviewFixGraphState,
    ) -> WorkflowReviewFixGraphState:
        return {"reviewers": self.load_reviewers()}

    async def _run_auto_review_round(
        self,
        state: WorkflowReviewFixGraphState,
    ) -> WorkflowReviewFixGraphState:
        reviewers = state.get("reviewers")
        if reviewers is None:
            raise ConfigurationError("Workflow review/fix runtime missing reviewers")
        try:
            aggregated = await self.run_review_round(
                self.generated_content,
                reviewers,
                "auto_review",
            )
        except ModelFallbackExhaustedError as exc:
            return {
                "review_outcome": self.resolve_model_fallback_review_outcome(
                    exc,
                    self.generated_content,
                    "generated",
                )
            }
        return {"aggregated": aggregated}

    def _resolve_auto_review_outcome(
        self,
        state: WorkflowReviewFixGraphState,
    ) -> WorkflowReviewFixGraphState:
        if state.get("review_outcome") is not None:
            return {}
        aggregated = state.get("aggregated")
        if aggregated is None:
            raise ConfigurationError("Workflow review/fix runtime missing auto review result")
        if aggregated.overall_status == "passed":
            return {"review_outcome": ReviewCycleOutcome("passed", self.generated_content, "generated")}
        if aggregated.execution_failures:
            return {
                "review_outcome": ReviewCycleOutcome(
                    "pause",
                    self.generated_content,
                    "generated",
                    failure_message="自动审核执行失败",
                )
            }
        if not self.resolve_auto_fix_enabled():
            return {
                "review_outcome": ReviewCycleOutcome(
                    "pause",
                    self.generated_content,
                    "generated",
                    failure_message="自动审核未通过",
                )
            }
        return {
            "current_content": self.generated_content,
            "content_source": "generated",
            "fix_attempt": 1,
            "max_fix_attempts": self.resolve_max_fix_attempts(),
        }

    def _route_after_auto_review_outcome(self, state: WorkflowReviewFixGraphState) -> str:
        if state.get("review_outcome") is not None:
            return "finish"
        return "run_fix_attempt"

    async def _run_fix_attempt(
        self,
        state: WorkflowReviewFixGraphState,
    ) -> WorkflowReviewFixGraphState:
        current_content = state.get("current_content")
        aggregated = state.get("aggregated")
        fix_attempt = state.get("fix_attempt")
        max_fix_attempts = state.get("max_fix_attempts")
        content_source = state.get("content_source")
        if (
            current_content is None
            or aggregated is None
            or fix_attempt is None
            or max_fix_attempts is None
            or content_source is None
        ):
            raise ConfigurationError("Workflow review/fix runtime missing fix attempt state")
        try:
            fixed_content = await self.run_fix_attempt(
                current_content,
                aggregated,
                fix_attempt,
                max_fix_attempts,
            )
        except ModelFallbackExhaustedError as exc:
            return {
                "review_outcome": self.resolve_model_fallback_review_outcome(
                    exc,
                    current_content,
                    content_source,
                )
            }
        return {
            "current_content": fixed_content,
            "content_source": "auto_fix",
        }

    def _route_after_fix_attempt(self, state: WorkflowReviewFixGraphState) -> str:
        if state.get("review_outcome") is not None:
            return "finish"
        return "run_re_review_round"

    async def _run_re_review_round(
        self,
        state: WorkflowReviewFixGraphState,
    ) -> WorkflowReviewFixGraphState:
        reviewers = state.get("reviewers")
        aggregated = state.get("aggregated")
        current_content = state.get("current_content")
        content_source = state.get("content_source")
        fix_attempt = state.get("fix_attempt")
        if (
            reviewers is None
            or aggregated is None
            or current_content is None
            or content_source is None
            or fix_attempt is None
        ):
            raise ConfigurationError("Workflow review/fix runtime missing re-review state")
        re_reviewers = self.select_re_reviewers(reviewers, aggregated)
        try:
            re_review_aggregated = await self.run_review_round(
                current_content,
                re_reviewers,
                f"auto_re_review_{fix_attempt}",
            )
        except ModelFallbackExhaustedError as exc:
            return {
                "review_outcome": self.resolve_model_fallback_review_outcome(
                    exc,
                    current_content,
                    content_source,
                )
            }
        return {"aggregated": re_review_aggregated}

    def _resolve_re_review_outcome(
        self,
        state: WorkflowReviewFixGraphState,
    ) -> WorkflowReviewFixGraphState:
        if state.get("review_outcome") is not None:
            return {}
        aggregated = state.get("aggregated")
        current_content = state.get("current_content")
        fix_attempt = state.get("fix_attempt")
        max_fix_attempts = state.get("max_fix_attempts")
        if (
            aggregated is None
            or current_content is None
            or fix_attempt is None
            or max_fix_attempts is None
        ):
            raise ConfigurationError("Workflow review/fix runtime missing re-review outcome state")
        if aggregated.overall_status == "passed":
            return {"review_outcome": ReviewCycleOutcome("passed", current_content, "auto_fix")}
        if aggregated.execution_failures:
            return {
                "review_outcome": ReviewCycleOutcome(
                    "pause",
                    current_content,
                    "auto_fix",
                    failure_message="自动复审执行失败",
                )
            }
        if fix_attempt >= max_fix_attempts:
            return {"review_outcome": self.resolve_fix_failure(current_content)}
        return {"fix_attempt": fix_attempt + 1}

    def _route_after_re_review_outcome(self, state: WorkflowReviewFixGraphState) -> str:
        if state.get("review_outcome") is not None:
            return "finish"
        return "run_fix_attempt"

    def _finish(
        self,
        state: WorkflowReviewFixGraphState,
    ) -> WorkflowReviewFixGraphState:
        if state.get("review_outcome") is None:
            raise ConfigurationError("Workflow review/fix runtime finish called without review outcome")
        return state
