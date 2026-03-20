from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .errors import ConfigurationError
from .tool_provider import ToolProvider

LLM_GENERATE_TOOL = "llm.generate"


class CompletionCallable(Protocol):
    async def __call__(self, **kwargs: Any) -> Any: ...


@dataclass(frozen=True)
class LLMRequest:
    prompt: str
    model_name: str
    provider: str | None
    api_key: str
    base_url: str | None
    system_prompt: str | None
    response_format: str
    temperature: float | None
    max_tokens: int | None


class LLMToolProvider(ToolProvider):
    def __init__(
        self,
        *,
        completion_callable: CompletionCallable | None = None,
    ) -> None:
        self.completion_callable = completion_callable or _default_completion_callable

    async def execute(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        if tool_name != LLM_GENERATE_TOOL:
            raise ConfigurationError(f"Unsupported tool: {tool_name}")
        request = _build_request(params)
        response = await self.completion_callable(**_to_completion_payload(request))
        return _normalize_response(response, request)

    def list_tools(self) -> list[str]:
        return [LLM_GENERATE_TOOL]


def _build_request(params: dict[str, Any]) -> LLMRequest:
    prompt = _require_non_empty_string(params.get("prompt"), "prompt")
    model = _require_dict(params.get("model"), "model")
    credential = _require_dict(params.get("credential"), "credential")
    return LLMRequest(
        prompt=prompt,
        model_name=_require_non_empty_string(model.get("name"), "model.name"),
        provider=_optional_string(model.get("provider")),
        api_key=_require_non_empty_string(credential.get("api_key"), "credential.api_key"),
        base_url=_optional_string(credential.get("base_url")),
        system_prompt=_optional_string(params.get("system_prompt")),
        response_format=_optional_string(params.get("response_format")) or "text",
        temperature=_optional_float(model.get("temperature")),
        max_tokens=_optional_int(model.get("max_tokens")),
    )


def _to_completion_payload(request: LLMRequest) -> dict[str, Any]:
    messages = []
    if request.system_prompt:
        messages.append({"role": "system", "content": request.system_prompt})
    messages.append({"role": "user", "content": request.prompt})
    payload: dict[str, Any] = {
        "model": request.model_name,
        "messages": messages,
        "api_key": request.api_key,
    }
    if request.provider:
        payload["custom_llm_provider"] = request.provider
    if request.base_url:
        payload["base_url"] = request.base_url
    if request.temperature is not None:
        payload["temperature"] = request.temperature
    if request.max_tokens is not None:
        payload["max_tokens"] = request.max_tokens
    if request.response_format == "json_object":
        payload["response_format"] = {"type": "json_object"}
    return payload


def _normalize_response(response: Any, request: LLMRequest) -> dict[str, Any]:
    usage = _extract_usage(response)
    return {
        "content": _extract_text(response),
        "model_name": request.model_name,
        "provider": request.provider,
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "total_tokens": usage["total_tokens"],
    }


def _extract_text(response: Any) -> str:
    choice = _extract_first_choice(response)
    message = choice.get("message")
    if not isinstance(message, dict):
        raise ConfigurationError("LLM response is missing message content")
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict)
        )
    raise ConfigurationError("LLM response content must be string or list")


def _extract_first_choice(response: Any) -> dict[str, Any]:
    choices = response.get("choices") if isinstance(response, dict) else getattr(response, "choices", None)
    if not isinstance(choices, list) or not choices:
        raise ConfigurationError("LLM response is missing choices")
    choice = choices[0]
    if isinstance(choice, dict):
        return choice
    message = getattr(choice, "message", None)
    return {"message": _message_to_dict(message)}


def _message_to_dict(message: Any) -> dict[str, Any]:
    if isinstance(message, dict):
        return message
    return {"content": getattr(message, "content", None)}


def _extract_usage(response: Any) -> dict[str, int | None]:
    raw_usage = response.get("usage") if isinstance(response, dict) else getattr(response, "usage", None)
    if raw_usage is None:
        return {"input_tokens": None, "output_tokens": None, "total_tokens": None}
    if not isinstance(raw_usage, dict):
        raw_usage = {
            "prompt_tokens": getattr(raw_usage, "prompt_tokens", None),
            "completion_tokens": getattr(raw_usage, "completion_tokens", None),
            "total_tokens": getattr(raw_usage, "total_tokens", None),
        }
    return {
        "input_tokens": _optional_int(raw_usage.get("prompt_tokens")),
        "output_tokens": _optional_int(raw_usage.get("completion_tokens")),
        "total_tokens": _optional_int(raw_usage.get("total_tokens")),
    }


def _require_dict(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigurationError(f"{field_name} must be an object")
    return value


def _require_non_empty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{field_name} must be a non-empty string")
    return value.strip()


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigurationError("Expected string value")
    stripped = value.strip()
    return stripped or None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ConfigurationError("Expected numeric value")
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError("Expected integer value")
    return value


async def _default_completion_callable(**kwargs: Any) -> Any:
    try:
        from litellm import acompletion
    except ImportError as exc:  # pragma: no cover
        raise ConfigurationError("litellm is not installed") from exc
    return await acompletion(**kwargs)
