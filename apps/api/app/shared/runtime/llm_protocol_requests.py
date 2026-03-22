from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlsplit

from .llm_endpoint_policy import normalize_custom_base_url
from .llm_protocol_types import (
    DEFAULT_BASE_URLS,
    JSON_OBJECT_RESPONSE_FORMAT,
    LLMConnection,
    LLMGenerateRequest,
    PreparedLLMHttpRequest,
    VERIFY_MODEL_REPLY,
    normalize_api_dialect,
    resolve_model_name,
)


def prepare_generation_request(request: LLMGenerateRequest) -> PreparedLLMHttpRequest:
    dialect = normalize_api_dialect(request.connection.api_dialect)
    if dialect == "openai_chat_completions":
        return _build_openai_chat_request(request)
    if dialect == "openai_responses":
        return _build_openai_responses_request(request)
    if dialect == "anthropic_messages":
        return _build_anthropic_messages_request(request)
    return _build_gemini_generate_content_request(request)


def build_verification_request(connection: LLMConnection) -> PreparedLLMHttpRequest:
    model_name = resolve_model_name(
        requested_model_name=None,
        default_model=connection.default_model,
        provider_label="credential verification",
    )
    return prepare_generation_request(
        LLMGenerateRequest(
            connection=connection,
            model_name=model_name,
            prompt=VERIFY_MODEL_REPLY,
            system_prompt="Reply with plain text ok.",
            response_format="text",
            temperature=0.0,
            max_tokens=8,
            top_p=1.0,
        )
    )


def _build_openai_chat_request(request: LLMGenerateRequest) -> PreparedLLMHttpRequest:
    body: dict[str, Any] = {
        "model": request.model_name,
        "messages": _build_openai_messages(request.prompt, request.system_prompt),
    }
    _merge_generation_params(body, request)
    if request.response_format == JSON_OBJECT_RESPONSE_FORMAT:
        body["response_format"] = {"type": "json_object"}
    return PreparedLLMHttpRequest(
        method="POST",
        url=_join_endpoint(request.connection, "/v1/chat/completions"),
        headers=_build_bearer_headers(request.connection.api_key),
        json_body=body,
    )


def _build_openai_responses_request(request: LLMGenerateRequest) -> PreparedLLMHttpRequest:
    body: dict[str, Any] = {
        "model": request.model_name,
        "input": [{"role": "user", "content": request.prompt}],
    }
    if request.system_prompt:
        body["instructions"] = request.system_prompt
    _merge_generation_params(body, request, max_tokens_field="max_output_tokens")
    if request.response_format == JSON_OBJECT_RESPONSE_FORMAT:
        body["text"] = {"format": {"type": "json_object"}}
    return PreparedLLMHttpRequest(
        method="POST",
        url=_join_endpoint(request.connection, "/v1/responses"),
        headers=_build_bearer_headers(request.connection.api_key),
        json_body=body,
    )


def _build_anthropic_messages_request(request: LLMGenerateRequest) -> PreparedLLMHttpRequest:
    body: dict[str, Any] = {
        "model": request.model_name,
        "max_tokens": request.max_tokens or 1024,
        "messages": [{"role": "user", "content": request.prompt}],
    }
    if request.system_prompt:
        body["system"] = request.system_prompt
    if request.temperature is not None:
        body["temperature"] = request.temperature
    if request.top_p is not None:
        body["top_p"] = request.top_p
    if request.stop:
        body["stop_sequences"] = request.stop
    return PreparedLLMHttpRequest(
        method="POST",
        url=_join_endpoint(request.connection, "/v1/messages"),
        headers=_build_anthropic_headers(request.connection.api_key),
        json_body=body,
    )


def _build_gemini_generate_content_request(request: LLMGenerateRequest) -> PreparedLLMHttpRequest:
    body: dict[str, Any] = {
        "contents": [{"parts": [{"text": request.prompt}]}],
    }
    generation_config = _build_gemini_generation_config(request)
    if generation_config:
        body["generationConfig"] = generation_config
    if request.system_prompt:
        body["system_instruction"] = {"parts": [{"text": request.system_prompt}]}
    return PreparedLLMHttpRequest(
        method="POST",
        url=_build_gemini_endpoint(request.connection, request.model_name),
        headers=_build_gemini_headers(request.connection.api_key),
        json_body=body,
    )


def _build_openai_messages(prompt: str, system_prompt: str | None) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    return messages


def _build_gemini_generation_config(request: LLMGenerateRequest) -> dict[str, Any]:
    config: dict[str, Any] = {}
    if request.temperature is not None:
        config["temperature"] = request.temperature
    if request.max_tokens is not None:
        config["maxOutputTokens"] = request.max_tokens
    if request.top_p is not None:
        config["topP"] = request.top_p
    if request.stop:
        config["stopSequences"] = request.stop
    if request.response_format == JSON_OBJECT_RESPONSE_FORMAT:
        config["responseMimeType"] = "application/json"
    return config


def _merge_generation_params(
    body: dict[str, Any],
    request: LLMGenerateRequest,
    *,
    max_tokens_field: str = "max_tokens",
) -> None:
    if request.temperature is not None:
        body["temperature"] = request.temperature
    if request.max_tokens is not None:
        body[max_tokens_field] = request.max_tokens
    if request.top_p is not None:
        body["top_p"] = request.top_p
    if request.stop:
        body["stop"] = request.stop


def _join_endpoint(connection: LLMConnection, endpoint: str) -> str:
    base_url = _resolve_base_url(connection)
    normalized_base = base_url.rstrip("/")
    endpoint_path = "/" + endpoint.lstrip("/")
    base_path = _resolve_base_path(normalized_base)
    if base_path.endswith(endpoint_path):
        return normalized_base
    if base_path.endswith("/v1") and endpoint_path.startswith("/v1/"):
        return f"{normalized_base}/{endpoint_path.removeprefix('/v1/')}"
    if base_path.endswith("/v1beta") and endpoint_path.startswith("/v1beta/"):
        return f"{normalized_base}/{endpoint_path.removeprefix('/v1beta/')}"
    return f"{normalized_base}{endpoint_path}"


def _build_gemini_endpoint(connection: LLMConnection, model_name: str) -> str:
    base_url = _resolve_base_url(connection).rstrip("/")
    if base_url.endswith(":generateContent"):
        return base_url
    endpoint = f"/v1beta/models/{quote(model_name, safe='')}:generateContent"
    return _join_endpoint(connection, endpoint)


def _resolve_base_url(connection: LLMConnection) -> str:
    custom_base_url = normalize_custom_base_url(connection.base_url)
    if custom_base_url is not None:
        return custom_base_url
    return DEFAULT_BASE_URLS[normalize_api_dialect(connection.api_dialect)]


def _resolve_base_path(base_url: str) -> str:
    path = urlsplit(base_url).path.rstrip("/")
    return path or "/"


def _build_bearer_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _build_anthropic_headers(api_key: str) -> dict[str, str]:
    return {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }


def _build_gemini_headers(api_key: str) -> dict[str, str]:
    return {"x-goog-api-key": api_key, "Content-Type": "application/json"}
