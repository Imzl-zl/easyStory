from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.interop.provider_interop_stream_support import build_stream_probe_request
from app.shared.runtime.llm.interop.provider_tool_conformance_support import (
    SUPPORTED_CONFORMANCE_PROBE_KINDS,
    build_conformance_probe_request,
    build_text_probe_request,
    build_tool_continuation_probe_followup_request,
    build_tool_continuation_probe_result_echo,
    normalize_conformance_probe_kind,
    normalize_text_probe_error_message,
    serialize_probe_response,
    use_buffered_text_probe_by_default,
    validate_tool_call_probe_response,
    validate_tool_continuation_probe_response,
    validate_tool_definition_probe_response,
    VERIFY_EMPTY_CONTENT_MESSAGE,
)
from app.shared.runtime.llm.interop.provider_interop_support import (
    DEFAULT_PROVIDER_INTEROP_CONFIG_PATH,
    DEFAULT_PROVIDER_INTEROP_ENV_PATH,
    DEFAULT_PROVIDER_INTEROP_RATE_LIMIT_PATH,
    ProviderInteropOverride,
    enforce_provider_interop_rate_limit,
    load_provider_interop_profiles,
    resolve_provider_interop_profile,
)
from app.shared.runtime.llm.llm_backend import AsyncLLMGenerateBackend, resolve_backend_selection
from app.shared.runtime.llm.litellm_backend import LiteLLMBackend, preview_litellm_call_spec
from app.shared.runtime.llm.llm_protocol import LLMGenerateRequest, NormalizedLLMResponse, prepare_generation_request
from app.shared.runtime.llm.llm_response_validation import raise_if_empty_tool_response
from app.shared.runtime.llm.native_http_backend import NativeHttpLLMBackend
from app.shared.settings import clear_settings_cache

APP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROBE_SYSTEM_PROMPT = "请直接回答用户问题，使用简洁中文。"
DEFAULT_LITELLM_BACKEND: AsyncLLMGenerateBackend = LiteLLMBackend()
DEFAULT_NATIVE_BACKEND: AsyncLLMGenerateBackend = NativeHttpLLMBackend()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe local provider interop profiles.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_list_command(subparsers)
    _add_probe_command(subparsers)
    return parser


def _add_list_command(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("list", help="List saved provider interop profiles.")
    _add_shared_paths(parser)


def _add_probe_command(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("probe", help="Probe one profile with optional overrides.")
    parser.add_argument("profile_id", help="Profile id from provider-interop.local.json")
    _add_shared_paths(parser)
    parser.add_argument(
        "--probe-kind",
        default="text_probe",
        choices=sorted(SUPPORTED_CONFORMANCE_PROBE_KINDS),
        help="Probe kind to execute",
    )
    parser.add_argument("--api-dialect", help="Temporarily override api_dialect")
    parser.add_argument("--base-url", help="Temporarily override base_url")
    parser.add_argument("--model", help="Temporarily override model name")
    parser.add_argument("--auth-strategy", help="Temporarily override auth strategy")
    parser.add_argument("--api-key-header-name", help="Temporarily override API key header name")
    parser.add_argument("--extra-headers", help="Temporarily merge extra headers from a JSON object")
    parser.add_argument("--prompt", help="Ask a real prompt instead of the fixed verification phrase")
    parser.add_argument("--system-prompt", help="Optional system prompt used with --prompt")
    output_mode_group = parser.add_mutually_exclusive_group()
    output_mode_group.add_argument(
        "--stream",
        action="store_true",
        dest="stream",
        help="Use the provider's streaming response mode (default)",
    )
    output_mode_group.add_argument(
        "--buffered",
        action="store_false",
        dest="stream",
        help="Force the provider's buffered JSON response mode",
    )
    parser.set_defaults(stream=None)
    parser.add_argument("--show-request", action="store_true", help="Print the prepared request")
    parser.add_argument("--print-response", action="store_true", help="Print the normalized response body")
    parser.add_argument("--dry-run", action="store_true", help="Build request only, do not send")
    parser.add_argument(
        "--skip-rate-limit",
        action="store_true",
        help="Skip local per-profile rate-limit guard",
    )


def _add_shared_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config",
        default=str(_default_path(DEFAULT_PROVIDER_INTEROP_CONFIG_PATH)),
        help="Profile config path",
    )
    parser.add_argument(
        "--env-file",
        default=str(_default_path(DEFAULT_PROVIDER_INTEROP_ENV_PATH)),
        help="Local env file path",
    )
    parser.add_argument(
        "--rate-limit-file",
        default=str(_default_path(DEFAULT_PROVIDER_INTEROP_RATE_LIMIT_PATH)),
        help="Local rate-limit state path",
    )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "list":
            _list_profiles(args)
            return 0
        return asyncio.run(_probe_profile(args))
    except ConfigurationError as exc:
        raise SystemExit(str(exc)) from exc
    except httpx.RequestError as exc:
        raise SystemExit(f"Request failed: {exc}") from exc


def _list_profiles(args: argparse.Namespace) -> None:
    profiles = load_provider_interop_profiles(Path(args.config))
    payload = [
        {
            "id": profile.id,
            "provider": profile.provider,
            "api_dialect": profile.api_dialect,
            "base_url": profile.base_url,
            "default_model": profile.default_model,
            "api_key_env": profile.api_key_env,
            "auth_strategy": profile.auth_strategy,
            "api_key_header_name": profile.api_key_header_name,
            "extra_headers": _mask_headers(profile.extra_headers or {}),
            "max_requests_per_minute": profile.max_requests_per_minute,
            "notes": profile.notes,
        }
        for profile in profiles
    ]
    print(json.dumps(payload, ensure_ascii=False, indent=2))


async def _probe_profile(args: argparse.Namespace) -> int:
    _apply_local_env_file(Path(args.env_file))
    resolved = resolve_provider_interop_profile(
        args.profile_id,
        config_path=Path(args.config),
        env_path=Path(args.env_file),
        override=_build_override(args),
    )
    probe_kind = normalize_conformance_probe_kind(args.probe_kind)
    if probe_kind == "text_probe":
        return await _probe_text_profile(args, resolved)
    _ensure_conformance_probe_args(args, probe_kind)
    return await _probe_tool_conformance_profile(args, resolved, probe_kind=probe_kind)


async def _probe_text_profile(args: argparse.Namespace, resolved) -> int:
    request = build_text_probe_request(
        resolved.connection,
        model_name=resolved.model_name,
        prompt=args.prompt,
        system_prompt=_resolve_system_prompt(args),
    )
    effective_stream = _resolve_effective_stream_mode(request, requested_stream=args.stream)
    if args.show_request or args.dry_run:
        print(_render_staged_request("initial", request, stream=effective_stream))
    if args.dry_run:
        return 0
    _enforce_rate_limit_if_needed(args, resolved)
    normalized = await _execute_probe_request(
        request,
        probe_kind="text_probe",
        print_response=args.print_response,
        stream=effective_stream,
    )
    _validate_text_probe_response(normalized)
    print(
        json.dumps(
            {
                "profile_id": resolved.profile_id,
                "provider": resolved.provider,
                "model_name": resolved.model_name,
                "probe_kind": "text_probe",
                "stream": effective_stream,
                **serialize_probe_response(normalized),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


async def _probe_tool_conformance_profile(args: argparse.Namespace, resolved, *, probe_kind: str) -> int:
    initial_request = build_conformance_probe_request(
        resolved.connection,
        model_name=resolved.model_name,
        probe_kind=probe_kind,
    )
    effective_stream = _resolve_conformance_stream_mode(args.stream)
    if args.show_request or args.dry_run:
        print(_render_staged_request("initial", initial_request, stream=effective_stream))
    if args.dry_run:
        return 0
    _enforce_rate_limit_if_needed(args, resolved)
    try:
        initial_response = await _execute_probe_request(
            initial_request,
            probe_kind=probe_kind,
            print_response=args.print_response,
            stream=effective_stream,
        )
        if probe_kind == "tool_definition_probe":
            validate_tool_definition_probe_response(initial_response)
    except ConfigurationError as exc:
        raise ConfigurationError(f"{probe_kind} initial stage failed: {exc}") from exc
    if probe_kind == "tool_definition_probe":
        payload = {
            "profile_id": resolved.profile_id,
            "provider": resolved.provider,
            "model_name": resolved.model_name,
            "probe_kind": probe_kind,
            "stream": effective_stream,
            "initial": serialize_probe_response(initial_response),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    try:
        validate_tool_call_probe_response(initial_response)
    except ConfigurationError as exc:
        raise ConfigurationError(f"{probe_kind} initial stage failed: {exc}") from exc
    if probe_kind == "tool_call_probe":
        payload = {
            "profile_id": resolved.profile_id,
            "provider": resolved.provider,
            "model_name": resolved.model_name,
            "probe_kind": probe_kind,
            "stream": effective_stream,
            "initial": serialize_probe_response(initial_response),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    result_echo = build_tool_continuation_probe_result_echo()
    try:
        followup_request = build_tool_continuation_probe_followup_request(
            resolved.connection,
            model_name=resolved.model_name,
            initial_response=initial_response,
            result_echo=result_echo,
        )
    except ConfigurationError as exc:
        raise ConfigurationError(f"{probe_kind} follow-up request build failed: {exc}") from exc
    if args.show_request:
        print(_render_staged_request("followup", followup_request, stream=effective_stream))
    _enforce_rate_limit_if_needed(args, resolved)
    try:
        followup_response = await _execute_probe_request(
            followup_request,
            probe_kind=probe_kind,
            print_response=args.print_response,
            stream=effective_stream,
        )
        validate_tool_continuation_probe_response(
            followup_response,
            expected_echo=result_echo,
        )
    except ConfigurationError as exc:
        raise ConfigurationError(f"{probe_kind} follow-up stage failed: {exc}") from exc
    payload = {
        "profile_id": resolved.profile_id,
        "provider": resolved.provider,
        "model_name": resolved.model_name,
        "probe_kind": probe_kind,
        "stream": effective_stream,
        "initial": serialize_probe_response(initial_response),
        "followup": serialize_probe_response(followup_response),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


async def _execute_probe_request(
    request: LLMGenerateRequest,
    *,
    probe_kind: str,
    print_response: bool,
    stream: bool,
) -> NormalizedLLMResponse:
    backend = _resolve_backend(request)
    if not stream:
        normalized = await backend.generate(request)
        if probe_kind != "text_probe":
            raise_if_empty_tool_response(
                has_tools=bool(request.tools),
                content=normalized.content,
                tool_calls=normalized.tool_calls,
            )
        if print_response:
            print(_render_response(normalized))
        return normalized
    terminal_response: NormalizedLLMResponse | None = None
    stream_deltas: list[str] = []
    async for event in backend.generate_stream(request):
        if event.delta:
            stream_deltas.append(event.delta)
        if event.terminal_response is not None:
            terminal_response = event.terminal_response
    if terminal_response is None:
        raise ConfigurationError("Streaming backend completed without terminal response")
    if probe_kind != "text_probe":
        raise_if_empty_tool_response(
            has_tools=bool(request.tools),
            content=terminal_response.content,
            tool_calls=terminal_response.tool_calls,
        )
    if print_response:
        print(_render_stream_response(stream_deltas, terminal_response))
    return terminal_response


def _validate_text_probe_response(response: NormalizedLLMResponse) -> None:
    actual_reply = response.content.strip()
    if not actual_reply:
        raise ConfigurationError(VERIFY_EMPTY_CONTENT_MESSAGE)
    upstream_error = normalize_text_probe_error_message(actual_reply)
    if upstream_error is not None:
        raise ConfigurationError(upstream_error)


def _resolve_backend(request: LLMGenerateRequest) -> AsyncLLMGenerateBackend:
    selection = resolve_backend_selection(request)
    if selection.backend_key == "native_http":
        return DEFAULT_NATIVE_BACKEND
    return DEFAULT_LITELLM_BACKEND




def _resolve_conformance_stream_mode(requested_stream: bool | None) -> bool:
    if requested_stream is None:
        return True
    return requested_stream


def _resolve_effective_stream_mode(request: LLMGenerateRequest, *, requested_stream: bool | None) -> bool:
    if requested_stream is not None:
        return requested_stream
    if use_buffered_text_probe_by_default(request.connection.api_dialect):
        return False
    return True

def _render_staged_request(stage: str, request: LLMGenerateRequest, *, stream: bool) -> str:
    selection = resolve_backend_selection(request)
    payload = {
        "stage": stage,
        "stream": stream,
        "backend": {
            "key": selection.backend_key,
            "reason": selection.reason,
        },
        "request": _serialize_staged_request(request, stream=stream, backend_key=selection.backend_key),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _serialize_staged_request(
    request: LLMGenerateRequest,
    *,
    stream: bool,
    backend_key: str,
) -> dict[str, Any]:
    if backend_key == "native_http":
        prepared_request = prepare_generation_request(request)
        if stream:
            prepared_request = build_stream_probe_request(
                prepared_request,
                api_dialect=request.connection.api_dialect,
            )
        return {
            "kind": "prepared_http_request",
            "method": prepared_request.method,
            "url": prepared_request.url,
            "headers": _mask_headers(prepared_request.headers),
            "json_body": prepared_request.json_body,
        }
    preview = preview_litellm_call_spec(request)
    preview_kwargs = dict(preview["call_kwargs"])
    if "api_key" in preview_kwargs:
        preview_kwargs["api_key"] = _mask_secret(str(preview_kwargs["api_key"]))
    if "extra_headers" in preview_kwargs and isinstance(preview_kwargs["extra_headers"], dict):
        preview_kwargs["extra_headers"] = _mask_headers(preview_kwargs["extra_headers"])
    return {
        "kind": "llm_generate_request",
        "litellm_preview": {
            "call_kind": preview["call_kind"],
            "output_api_dialect": preview["output_api_dialect"],
            "tool_name_aliases": preview["tool_name_aliases"],
            "call_kwargs": preview_kwargs,
        },
        "prompt": request.prompt,
        "system_prompt": request.system_prompt,
        "response_format": request.response_format,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
        "top_p": request.top_p,
        "reasoning_effort": request.reasoning_effort,
        "thinking_level": request.thinking_level,
        "thinking_budget": request.thinking_budget,
        "stop": request.stop,
        "force_tool_call": request.force_tool_call,
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
                "strict": tool.strict,
            }
            for tool in request.tools
        ],
        "continuation_items": request.continuation_items,
        "provider_continuation_state": request.provider_continuation_state,
        "connection": {
            "provider": request.connection.provider,
            "api_dialect": request.connection.api_dialect,
            "api_key": _mask_secret(request.connection.api_key),
            "base_url": request.connection.base_url,
            "default_model": request.connection.default_model,
            "auth_strategy": request.connection.auth_strategy,
            "api_key_header_name": request.connection.api_key_header_name,
            "extra_headers": _mask_headers(request.connection.extra_headers or {}),
            "user_agent_override": request.connection.user_agent_override,
            "client_name": request.connection.client_name,
            "client_version": request.connection.client_version,
            "runtime_kind": request.connection.runtime_kind,
            "interop_profile": request.connection.interop_profile,
            "context_window_tokens": request.connection.context_window_tokens,
        },
    }


def _render_response(normalized: NormalizedLLMResponse) -> str:
    payload = {
        "normalized": serialize_probe_response(normalized),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _render_stream_response(deltas: list[str], normalized: NormalizedLLMResponse) -> str:
    payload = {
        "stream_text": "".join(deltas),
        "normalized": serialize_probe_response(normalized),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _build_override(args: argparse.Namespace) -> ProviderInteropOverride:
    return ProviderInteropOverride(
        api_dialect=args.api_dialect,
        base_url=args.base_url,
        model_name=args.model,
        auth_strategy=args.auth_strategy,
        api_key_header_name=args.api_key_header_name,
        extra_headers=_parse_extra_headers_json(args.extra_headers),
    )


def _resolve_system_prompt(args: argparse.Namespace) -> str | None:
    if args.prompt is None:
        return None
    if args.system_prompt is not None:
        return args.system_prompt
    return DEFAULT_PROBE_SYSTEM_PROMPT


def _parse_extra_headers_json(raw_value: str | None) -> dict[str, str] | None:
    if raw_value is None:
        return None
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise ConfigurationError("--extra-headers must be a valid JSON object") from exc
    if not isinstance(payload, dict):
        raise ConfigurationError("--extra-headers must be a JSON object")
    return payload


def _ensure_conformance_probe_args(args: argparse.Namespace, probe_kind: str) -> None:
    if args.prompt is not None or args.system_prompt is not None:
        raise ConfigurationError(
            f"--prompt/--system-prompt 只支持 text_probe；当前 probe_kind={probe_kind}"
        )


def _enforce_rate_limit_if_needed(args: argparse.Namespace, resolved) -> None:
    if args.skip_rate_limit:
        return
    enforce_provider_interop_rate_limit(
        profile_id=resolved.profile_id,
        max_requests_per_minute=resolved.max_requests_per_minute,
        rate_limit_path=Path(args.rate_limit_file),
    )


def _mask_headers(headers: dict[str, str]) -> dict[str, str]:
    return {
        key: _mask_secret(value) if _is_secret_header(key) else value
        for key, value in headers.items()
    }


def _is_secret_header(header_name: str) -> bool:
    normalized = header_name.lower()
    return normalized == "authorization" or "key" in normalized


def _mask_secret(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def _default_path(path: Path) -> Path:
    return APP_ROOT / path


def _apply_local_env_file(env_path: Path) -> None:
    if not env_path.exists():
        clear_settings_cache()
        return
    for key, value in dotenv_values(env_path).items():
        if value is None:
            continue
        os.environ[key] = value
    clear_settings_cache()


if __name__ == "__main__":
    raise SystemExit(main())
