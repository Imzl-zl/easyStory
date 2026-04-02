from __future__ import annotations

from .llm_protocol_types import PreparedLLMHttpRequest

GEMINI_MINIMAL_THINKING_LEVEL = "minimal"


def apply_gemini_probe_thinking_config(
    request: PreparedLLMHttpRequest,
    model_name: str,
) -> PreparedLLMHttpRequest:
    body = dict(request.json_body)
    generation_config = dict(body.get("generationConfig") or {})
    generation_config["thinkingConfig"] = build_gemini_probe_thinking_config(model_name)
    body["generationConfig"] = generation_config
    return PreparedLLMHttpRequest(
        method=request.method,
        url=request.url,
        headers=request.headers,
        json_body=body,
    )


def build_gemini_probe_thinking_config(model_name: str) -> dict[str, int | str]:
    normalized_model = model_name.lower()
    if "2.5" in normalized_model:
        return {"thinkingBudget": 0}
    return {"thinkingLevel": GEMINI_MINIMAL_THINKING_LEVEL}
