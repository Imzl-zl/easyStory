import pytest

from app.modules.content.service.story_asset_generation_runtime import (
    StoryAssetGenerationRuntime,
)


async def _return_async(value):
    return value


@pytest.mark.asyncio
async def test_story_asset_generation_runtime_runs_generation_chain() -> None:
    call_log: list[object] = []
    skill = object()
    model = object()
    result = object()

    runtime = StoryAssetGenerationRuntime(
        ensure_dependencies=lambda: _return_async(call_log.append("deps")),
        resolve_generation_context=lambda: call_log.append("context") or (skill, model),
        build_prompt=lambda resolved_skill: _return_async(
            call_log.append(("prompt", resolved_skill)) or "prompt-text"
        ),
        generate_text=lambda resolved_model, prompt: _return_async(
            call_log.append(("generate", resolved_model, prompt)) or "generated-text"
        ),
        save_draft=lambda generated_text: _return_async(
            call_log.append(("save", generated_text)) or result
        ),
    )

    output = await runtime.run()

    assert output is result
    assert call_log == [
        "deps",
        "context",
        ("prompt", skill),
        ("generate", model, "prompt-text"),
        ("save", "generated-text"),
    ]
