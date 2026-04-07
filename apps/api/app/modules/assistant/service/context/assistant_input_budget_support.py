from __future__ import annotations

import json
from typing import Any

from app.shared.runtime.llm.llm_protocol import LLMContinuationSupport
from app.shared.runtime.token_counter import TokenCounter

DEFAULT_TOKEN_MODEL = "default"


def estimate_assistant_request_tokens(
    *,
    prompt: str,
    system_prompt: str | None,
    token_counter: TokenCounter,
    tools: list[dict[str, Any]] | None = None,
    continuation_items: list[dict[str, Any]] | None = None,
    continuation_support: LLMContinuationSupport | None = None,
    provider_continuation_state: dict[str, Any] | None = None,
) -> int:
    total = 0
    prompt_text = _resolve_prompt_projection(
        prompt=prompt,
        continuation_support=continuation_support,
        provider_continuation_state=provider_continuation_state,
    )
    if prompt_text:
        total += token_counter.count(prompt_text, DEFAULT_TOKEN_MODEL)
    if isinstance(system_prompt, str) and system_prompt.strip():
        total += token_counter.count(system_prompt.strip(), DEFAULT_TOKEN_MODEL)
    total += _estimate_json_tokens(tools, token_counter=token_counter)
    total += _estimate_json_tokens(
        _resolve_continuation_projection(
            continuation_items=continuation_items,
            continuation_support=continuation_support,
            provider_continuation_state=provider_continuation_state,
        ),
        token_counter=token_counter,
    )
    return total


def trim_text_to_token_budget(
    text: str,
    *,
    target_tokens: int,
    token_counter: TokenCounter,
) -> str:
    if token_counter.count(text, DEFAULT_TOKEN_MODEL) <= target_tokens:
        return text
    suffix = "\n..."
    low, high = 1, len(text)
    best = ""
    while low <= high:
        mid = (low + high) // 2
        candidate = text[:mid].rstrip() + suffix
        if token_counter.count(candidate, DEFAULT_TOKEN_MODEL) <= target_tokens:
            best = candidate
            low = mid + 1
            continue
        high = mid - 1
    return best or suffix.strip()


def _resolve_prompt_projection(
    *,
    prompt: str,
    continuation_support: LLMContinuationSupport | None,
    provider_continuation_state: dict[str, Any] | None,
) -> str:
    if _uses_provider_latest_items(continuation_support, provider_continuation_state):
        return ""
    return prompt


def _resolve_continuation_projection(
    *,
    continuation_items: list[dict[str, Any]] | None,
    continuation_support: LLMContinuationSupport | None,
    provider_continuation_state: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if _uses_provider_latest_items(continuation_support, provider_continuation_state):
        latest_items = provider_continuation_state.get("latest_items")
        if isinstance(latest_items, list):
            return [item for item in latest_items if isinstance(item, dict)]
        return []
    return list(continuation_items or [])


def _uses_provider_latest_items(
    continuation_support: LLMContinuationSupport | None,
    provider_continuation_state: dict[str, Any] | None,
) -> bool:
    if continuation_support is None or not isinstance(provider_continuation_state, dict):
        return False
    if continuation_support.continuation_mode == "runtime_replay":
        return False
    previous_response_id = provider_continuation_state.get("previous_response_id")
    return isinstance(previous_response_id, str) and previous_response_id.strip() != ""


def _estimate_json_tokens(
    value: Any,
    *,
    token_counter: TokenCounter,
) -> int:
    if value in (None, [], {}):
        return 0
    return token_counter.count(
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
        DEFAULT_TOKEN_MODEL,
    )
