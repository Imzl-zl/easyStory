from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.shared.runtime.errors import ConfigurationError


class StoryAssetGenerationGraphState(TypedDict, total=False):
    skill: Any
    model: Any
    prompt: str
    generated_text: str
    result: Any


class LangGraphStoryAssetGenerationRuntime:
    def __init__(
        self,
        *,
        ensure_dependencies: Callable[[], Awaitable[None]],
        resolve_generation_context: Callable[[], tuple[Any, Any]],
        build_prompt: Callable[[Any], Awaitable[str]],
        generate_text: Callable[[Any, str], Awaitable[str]],
        save_draft: Callable[[str], Awaitable[Any]],
    ) -> None:
        self.ensure_dependencies = ensure_dependencies
        self.resolve_generation_context = resolve_generation_context
        self.build_prompt = build_prompt
        self.generate_text = generate_text
        self.save_draft = save_draft
        self._graph = self._build_graph()

    async def run(self) -> Any:
        final_state = await self._graph.ainvoke({})
        if "result" not in final_state:
            raise ConfigurationError("Story asset generation runtime completed without result")
        return final_state["result"]

    def _build_graph(self):
        graph = StateGraph(StoryAssetGenerationGraphState)
        graph.add_node("ensure_dependencies", self._ensure_dependencies)
        graph.add_node("resolve_generation_context", self._resolve_generation_context)
        graph.add_node("build_prompt", self._build_prompt)
        graph.add_node("generate_text", self._generate_text)
        graph.add_node("save_draft", self._save_draft)
        graph.add_edge(START, "ensure_dependencies")
        graph.add_edge("ensure_dependencies", "resolve_generation_context")
        graph.add_edge("resolve_generation_context", "build_prompt")
        graph.add_edge("build_prompt", "generate_text")
        graph.add_edge("generate_text", "save_draft")
        graph.add_edge("save_draft", END)
        return graph.compile(name="story_asset_generation_runtime")

    async def _ensure_dependencies(
        self,
        _state: StoryAssetGenerationGraphState,
    ) -> StoryAssetGenerationGraphState:
        await self.ensure_dependencies()
        return {}

    def _resolve_generation_context(
        self,
        _state: StoryAssetGenerationGraphState,
    ) -> StoryAssetGenerationGraphState:
        skill, model = self.resolve_generation_context()
        return {
            "skill": skill,
            "model": model,
        }

    async def _build_prompt(
        self,
        state: StoryAssetGenerationGraphState,
    ) -> StoryAssetGenerationGraphState:
        skill = state.get("skill")
        if skill is None:
            raise ConfigurationError("Story asset generation runtime missing skill")
        return {"prompt": await self.build_prompt(skill)}

    async def _generate_text(
        self,
        state: StoryAssetGenerationGraphState,
    ) -> StoryAssetGenerationGraphState:
        model = state.get("model")
        prompt = state.get("prompt")
        if model is None or prompt is None:
            raise ConfigurationError("Story asset generation runtime missing model or prompt")
        return {
            "generated_text": await self.generate_text(model, prompt),
        }

    async def _save_draft(
        self,
        state: StoryAssetGenerationGraphState,
    ) -> StoryAssetGenerationGraphState:
        generated_text = state.get("generated_text")
        if generated_text is None:
            raise ConfigurationError("Story asset generation runtime missing generated text")
        return {"result": await self.save_draft(generated_text)}
