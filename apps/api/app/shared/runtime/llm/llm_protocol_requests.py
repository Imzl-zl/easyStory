from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlsplit

from ..errors import ConfigurationError
from .interop.tool_continuation_codec import (
    build_openai_responses_input as codec_build_openai_responses_input,
    collect_continuation_tool_names as codec_collect_continuation_tool_names,
    project_continuation_to_anthropic_messages as codec_project_continuation_to_anthropic_messages,
    project_continuation_to_gemini_contents as codec_project_continuation_to_gemini_contents,
    project_continuation_to_openai_chat_messages as codec_project_continuation_to_openai_chat_messages,
    read_latest_continuation_items as codec_read_latest_continuation_items,
    read_previous_response_id as codec_read_previous_response_id,
)
from .interop.tool_schema_compiler import compile_tool_parameters
from .interop.tool_name_codec import (
    build_tool_name_aliases,
    encode_tool_name,
)
from .llm_endpoint_policy import normalize_custom_base_url
from .llm_interop_profiles import LLMInteropCapabilities, resolve_interop_capabilities
from .llm_reasoning_validation import build_provider_native_reasoning_error
from .llm_protocol_types import (
    ANTHROPIC_VERSION,
    DEFAULT_BASE_URLS,
    JSON_OBJECT_RESPONSE_FORMAT,
    LLMConnection,
    LLMGenerateRequest,
    PreparedLLMHttpRequest,
    VERIFY_MAX_TOKENS,
    VERIFY_SYSTEM_PROMPT,
    VERIFY_USER_PROMPT,
    normalize_api_dialect,
    resolve_anthropic_default_max_tokens,
    resolve_api_key_header_name,
    resolve_auth_strategy,
    resolve_model_name,
)

USER_AGENT_HEADER_NAME = "User-Agent"
RUNTIME_KIND_LABELS = {
    "server-python": "server; python",
    "server-node": "server; node",
    "browser": "browser",
}


def prepare_generation_request(request: LLMGenerateRequest) -> PreparedLLMHttpRequest:
    dialect = normalize_api_dialect(request.connection.api_dialect)
    reasoning_error = build_provider_native_reasoning_error(
        provider=None,
        api_dialect=dialect,
        reasoning_effort=request.reasoning_effort,
        thinking_level=request.thinking_level,
        thinking_budget=request.thinking_budget,
    )
    if reasoning_error is not None:
        raise ConfigurationError(reasoning_error)
    capabilities = resolve_interop_capabilities(
        dialect,
        request.connection.interop_profile,
    )
    tool_name_aliases = build_tool_name_aliases(
        _collect_request_tool_names(request),
        policy=capabilities.tool_name_policy,
    )
    if dialect == "openai_chat_completions":
        return _build_openai_chat_request(
            request,
            capabilities=capabilities,
            tool_name_aliases=tool_name_aliases,
        )
    if dialect == "openai_responses":
        return _build_openai_responses_request(
            request,
            capabilities=capabilities,
            tool_name_aliases=tool_name_aliases,
        )
    if dialect == "anthropic_messages":
        return _build_anthropic_messages_request(
            request,
            capabilities=capabilities,
            tool_name_aliases=tool_name_aliases,
        )
    if dialect == "gemini_generate_content":
        return _build_gemini_generate_content_request(
            request,
            capabilities=capabilities,
            tool_name_aliases=tool_name_aliases,
        )
    raise ConfigurationError(f"Unsupported api_dialect for request preparation: {dialect}")


def build_verification_request(connection: LLMConnection) -> PreparedLLMHttpRequest:
    model_name = resolve_model_name(
        requested_model_name=None,
        default_model=connection.default_model,
        provider_label="credential verification",
    )
    api_dialect = normalize_api_dialect(connection.api_dialect)
    request = prepare_generation_request(
        LLMGenerateRequest(
            connection=connection,
            model_name=model_name,
            prompt=VERIFY_USER_PROMPT,
            system_prompt=VERIFY_SYSTEM_PROMPT,
            response_format="text",
            temperature=0.0,
            max_tokens=VERIFY_MAX_TOKENS,
            top_p=1.0,
            thinking_budget=0 if api_dialect == "gemini_generate_content" else None,
        )
    )
    # Gemini native endpoints can spend a large share of the verification budget
    # on hidden thinking and then terminate with MAX_TOKENS before returning a
    # stable baseline answer. Connection verification is intended to prove that
    # the endpoint can return ordinary text replies, so Gemini probes opt out of
    # native thinking explicitly while preserving the normal request shape.
    return request


def _build_openai_chat_request(
    request: LLMGenerateRequest,
    *,
    capabilities: LLMInteropCapabilities,
    tool_name_aliases: dict[str, str],
) -> PreparedLLMHttpRequest:
    body: dict[str, Any] = {
        "model": request.model_name,
        "messages": _build_openai_chat_messages(
            request,
            tool_name_aliases=tool_name_aliases,
            tool_name_policy=capabilities.tool_name_policy,
        ),
    }
    if request.tools:
        body["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": encode_tool_name(
                        tool.name,
                        tool_name_aliases=tool_name_aliases,
                        policy=capabilities.tool_name_policy,
                    ),
                    "description": tool.description,
                    "parameters": _compile_tool_parameters(tool.parameters, capabilities=capabilities),
                    "strict": tool.strict,
                },
            }
            for tool in request.tools
        ]
        body["parallel_tool_calls"] = capabilities.supports_parallel_tool_calls
        if request.force_tool_call:
            body["tool_choice"] = "required"
    if request.reasoning_effort is not None:
        body["reasoning_effort"] = request.reasoning_effort
    # Official OpenAI Chat Completions uses max_completion_tokens, while many
    # third-party OpenAI-compatible gateways still only accept max_tokens.
    _merge_generation_params(
        body,
        request,
        max_tokens_field=_resolve_openai_chat_max_tokens_field(request.connection),
    )
    if request.response_format == JSON_OBJECT_RESPONSE_FORMAT:
        body["response_format"] = {"type": "json_object"}
    return PreparedLLMHttpRequest(
        method="POST",
        url=_join_endpoint(request.connection, "/v1/chat/completions"),
        headers=_build_request_headers(request.connection),
        json_body=body,
        interop_profile=request.connection.interop_profile,
        tool_name_aliases=tool_name_aliases,
    )


def _build_openai_responses_request(
    request: LLMGenerateRequest,
    *,
    capabilities: LLMInteropCapabilities,
    tool_name_aliases: dict[str, str],
) -> PreparedLLMHttpRequest:
    body: dict[str, Any] = {
        "model": request.model_name,
        "input": _build_openai_responses_input(
            request,
            tool_name_aliases=tool_name_aliases,
            tool_name_policy=capabilities.tool_name_policy,
        ),
    }
    previous_response_id = codec_read_previous_response_id(request.provider_continuation_state)
    if previous_response_id is not None:
        body["previous_response_id"] = previous_response_id
    if request.tools:
        body["tools"] = [
            {
                "type": "function",
                "name": encode_tool_name(
                    tool.name,
                    tool_name_aliases=tool_name_aliases,
                    policy=capabilities.tool_name_policy,
                ),
                "description": tool.description,
                "parameters": _compile_tool_parameters(tool.parameters, capabilities=capabilities),
                "strict": tool.strict,
            }
            for tool in request.tools
        ]
        body["parallel_tool_calls"] = capabilities.supports_parallel_tool_calls
        if request.force_tool_call:
            body["tool_choice"] = "required"
    if request.reasoning_effort is not None:
        body["reasoning"] = {"effort": request.reasoning_effort}
    if request.system_prompt:
        body["instructions"] = request.system_prompt
    _merge_generation_params(body, request, max_tokens_field="max_output_tokens")
    if request.response_format == JSON_OBJECT_RESPONSE_FORMAT:
        body["text"] = {"format": {"type": "json_object"}}
    return PreparedLLMHttpRequest(
        method="POST",
        url=_join_endpoint(request.connection, "/v1/responses"),
        headers=_build_request_headers(request.connection),
        json_body=body,
        interop_profile=request.connection.interop_profile,
        tool_name_aliases=tool_name_aliases,
    )


def _build_anthropic_messages_request(
    request: LLMGenerateRequest,
    *,
    capabilities: LLMInteropCapabilities,
    tool_name_aliases: dict[str, str],
) -> PreparedLLMHttpRequest:
    body: dict[str, Any] = {
        "model": request.model_name,
        # Anthropic Messages requires max_tokens even when the caller does not
        # explicitly override output length.
        "max_tokens": (
            request.max_tokens
            if request.max_tokens is not None
            else resolve_anthropic_default_max_tokens(request.connection.context_window_tokens)
        ),
        "messages": _build_anthropic_messages(
            request,
            tool_name_aliases=tool_name_aliases,
            tool_name_policy=capabilities.tool_name_policy,
        ),
    }
    if request.tools:
        body["tools"] = [
            {
                "name": encode_tool_name(
                    tool.name,
                    tool_name_aliases=tool_name_aliases,
                    policy=capabilities.tool_name_policy,
                ),
                "description": tool.description,
                "input_schema": _compile_tool_parameters(tool.parameters, capabilities=capabilities),
            }
            for tool in request.tools
        ]
        if request.force_tool_call:
            body["tool_choice"] = {
                "type": "any",
                "disable_parallel_tool_use": True,
            }
    if request.system_prompt:
        body["system"] = [{"type": "text", "text": request.system_prompt}]
    if request.temperature is not None:
        body["temperature"] = request.temperature
    if request.top_p is not None:
        body["top_p"] = request.top_p
    if request.stop:
        body["stop_sequences"] = request.stop
    return PreparedLLMHttpRequest(
        method="POST",
        url=_join_endpoint(request.connection, "/v1/messages"),
        headers=_build_request_headers(
            request.connection,
            extra_headers={"anthropic-version": ANTHROPIC_VERSION},
        ),
        json_body=body,
        interop_profile=request.connection.interop_profile,
        tool_name_aliases=tool_name_aliases,
    )


def _build_gemini_generate_content_request(
    request: LLMGenerateRequest,
    *,
    capabilities: LLMInteropCapabilities,
    tool_name_aliases: dict[str, str],
) -> PreparedLLMHttpRequest:
    body: dict[str, Any] = {
        "contents": _build_gemini_contents(
            request,
            tool_name_aliases=tool_name_aliases,
            tool_name_policy=capabilities.tool_name_policy,
        ),
    }
    generation_config = _build_gemini_generation_config(request)
    if generation_config:
        body["generationConfig"] = generation_config
    if request.tools:
        body["tools"] = [
            {
                "functionDeclarations": _build_gemini_function_declarations(
                    request,
                    capabilities=capabilities,
                    tool_name_aliases=tool_name_aliases,
                )
            }
        ]
        if request.force_tool_call:
            body["toolConfig"] = _build_gemini_force_tool_config(
                request,
                tool_name_aliases=tool_name_aliases,
                tool_name_policy=capabilities.tool_name_policy,
            )
    if request.system_prompt:
        body["system_instruction"] = {"parts": [{"text": request.system_prompt}]}
    return PreparedLLMHttpRequest(
        method="POST",
        url=_build_gemini_endpoint(request.connection, request.model_name),
        headers=_build_request_headers(request.connection),
        json_body=body,
        interop_profile=request.connection.interop_profile,
        tool_name_aliases=tool_name_aliases,
    )


def _build_gemini_function_declarations(
    request: LLMGenerateRequest,
    *,
    capabilities: LLMInteropCapabilities,
    tool_name_aliases: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        {
            "name": encode_tool_name(
                tool.name,
                tool_name_aliases=tool_name_aliases,
                policy=capabilities.tool_name_policy,
            ),
            "description": tool.description,
            "parameters": _compile_tool_parameters(tool.parameters, capabilities=capabilities),
        }
        for tool in request.tools
    ]


def _build_gemini_force_tool_config(
    request: LLMGenerateRequest,
    *,
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> dict[str, Any]:
    allowed_tool_names = [
        encode_tool_name(
            tool.name,
            tool_name_aliases=tool_name_aliases,
            policy=tool_name_policy,
        )
        for tool in request.tools
    ]
    return {
        "functionCallingConfig": {
            "mode": "ANY",
            "allowedFunctionNames": allowed_tool_names,
        }
    }


def _build_openai_chat_messages(
    request: LLMGenerateRequest,
    *,
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    if request.system_prompt:
        messages.append({"role": "system", "content": request.system_prompt})
    if request.prompt.strip():
        messages.append({"role": "user", "content": request.prompt})
    messages.extend(
        codec_project_continuation_to_openai_chat_messages(
            request.continuation_items,
            tool_name_aliases=tool_name_aliases,
            tool_name_policy=tool_name_policy,
        )
    )
    return messages


def _build_anthropic_messages(
    request: LLMGenerateRequest,
    *,
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    if request.prompt.strip():
        messages.append(
            {
                "role": "user",
                "content": [{"type": "text", "text": request.prompt}],
            }
        )
    messages.extend(
        codec_project_continuation_to_anthropic_messages(
            request.continuation_items,
            tool_name_aliases=tool_name_aliases,
            tool_name_policy=tool_name_policy,
        )
    )
    return messages


def _build_gemini_contents(
    request: LLMGenerateRequest,
    *,
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> list[dict[str, Any]]:
    contents: list[dict[str, Any]] = []
    if request.prompt.strip():
        contents.append({"role": "user", "parts": [{"text": request.prompt}]})
    contents.extend(
        codec_project_continuation_to_gemini_contents(
            request.continuation_items,
            tool_name_aliases=tool_name_aliases,
            tool_name_policy=tool_name_policy,
        )
    )
    return contents


def _compile_tool_parameters(
    parameters: dict[str, Any],
    *,
    capabilities: LLMInteropCapabilities,
) -> dict[str, Any]:
    return compile_tool_parameters(
        parameters,
        mode=capabilities.tool_schema_mode,
    )


def _build_openai_responses_input(
    request: LLMGenerateRequest,
    *,
    tool_name_aliases: dict[str, str],
    tool_name_policy: str,
) -> list[dict[str, Any]]:
    return codec_build_openai_responses_input(
        request,
        tool_name_aliases=tool_name_aliases,
        tool_name_policy=tool_name_policy,
    )


def _collect_request_tool_names(request: LLMGenerateRequest) -> list[str]:
    names = [tool.name for tool in request.tools]
    names.extend(codec_collect_continuation_tool_names(request.continuation_items))
    names.extend(codec_collect_continuation_tool_names(codec_read_latest_continuation_items(request)))
    return names


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
    thinking_config = _build_gemini_thinking_config(request)
    if thinking_config is not None:
        config["thinkingConfig"] = thinking_config
    return config


def _build_gemini_thinking_config(request: LLMGenerateRequest) -> dict[str, Any] | None:
    if request.thinking_level is not None:
        return {"thinkingLevel": request.thinking_level}
    if request.thinking_budget is not None:
        return {"thinkingBudget": request.thinking_budget}
    return None


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


def _resolve_openai_chat_max_tokens_field(connection: LLMConnection) -> str:
    hostname = (urlsplit(_resolve_base_url(connection)).hostname or "").lower()
    if hostname == "api.openai.com":
        return "max_completion_tokens"
    return "max_tokens"


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


def _build_request_headers(
    connection: LLMConnection,
    *,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, str]:
    headers = dict(connection.extra_headers or {})
    headers["Content-Type"] = "application/json"
    headers.update(_build_auth_headers(connection))
    user_agent = _build_user_agent(connection)
    if user_agent is not None:
        headers[USER_AGENT_HEADER_NAME] = user_agent
    if extra_headers:
        headers.update(extra_headers)
    return headers


def _build_user_agent(connection: LLMConnection) -> str | None:
    if connection.user_agent_override is not None:
        return connection.user_agent_override
    if connection.client_name is None:
        return None
    user_agent = connection.client_name
    if connection.client_version:
        user_agent = f"{user_agent}/{connection.client_version}"
    if connection.runtime_kind:
        user_agent = f"{user_agent} ({RUNTIME_KIND_LABELS[connection.runtime_kind]})"
    return user_agent


def _build_auth_headers(connection: LLMConnection) -> dict[str, str]:
    strategy = resolve_auth_strategy(connection.api_dialect, connection.auth_strategy)
    if strategy == "bearer":
        return {"Authorization": f"Bearer {connection.api_key}"}
    header_name = resolve_api_key_header_name(
        api_dialect=connection.api_dialect,
        auth_strategy=connection.auth_strategy,
        api_key_header_name=connection.api_key_header_name,
    )
    if header_name is None:
        raise ConfigurationError("Missing API key header name for auth strategy")
    return {header_name: connection.api_key}
