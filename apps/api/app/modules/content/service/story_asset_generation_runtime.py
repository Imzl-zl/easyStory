from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.shared.runtime.errors import ConfigurationError

class StoryAssetGenerationRuntime:
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

    async def run(self) -> Any:
        await self.ensure_dependencies()
        skill, model = self.resolve_generation_context()
        if skill is None or model is None:
            raise ConfigurationError("Story asset generation runtime missing generation context")
        prompt = await self.build_prompt(skill)
        generated_text = await self.generate_text(model, prompt)
        return await self.save_draft(generated_text)


LangGraphStoryAssetGenerationRuntime = StoryAssetGenerationRuntime
