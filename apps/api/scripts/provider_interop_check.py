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
from app.shared.runtime.llm.llm_protocol import parse_generation_response, send_json_http_request
from app.shared.runtime.llm.interop.provider_interop_stream_support import (
    build_stream_probe_request,
    execute_stream_probe_request,
)
from app.shared.runtime.llm.interop.provider_tool_conformance_support import (
    SUPPORTED_CONFORMANCE_PROBE_KINDS,
    build_tool_continuation_probe_result_echo,
    build_conformance_probe_request,
    build_tool_continuation_probe_followup_request,
    normalize_conformance_probe_kind,
    serialize_probe_response,
    validate_tool_call_probe_response,
    validate_tool_continuation_probe_response,
    validate_tool_definition_probe_response,
)
from app.shared.runtime.llm.interop.provider_interop_support import (
    DEFAULT_PROVIDER_INTEROP_CONFIG_PATH,
    DEFAULT_PROVIDER_INTEROP_ENV_PATH,
    DEFAULT_PROVIDER_INTEROP_RATE_LIMIT_PATH,
    ProviderInteropOverride,
    build_provider_interop_probe_request,
    enforce_provider_interop_rate_limit,
    load_provider_interop_profiles,
    resolve_provider_interop_profile,
)
from app.shared.settings import clear_settings_cache

APP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROBE_SYSTEM_PROMPT = "请直接回答用户问题，使用简洁中文。"


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
    parser.set_defaults(stream=True)
    parser.add_argument("--show-request", action="store_true", help="Print the prepared request")
    parser.add_argument("--print-response", action="store_true", help="Print the raw response body")
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
    request = build_provider_interop_probe_request(
        resolved,
        prompt=args.prompt,
        system_prompt=_resolve_system_prompt(args),
    )
    request = _maybe_build_stream_request(
        request,
        api_dialect=resolved.connection.api_dialect,
        stream=args.stream,
    )
    if args.show_request or args.dry_run:
        print(_render_staged_request("initial", request))
    if args.dry_run:
        return 0
    _enforce_rate_limit_if_needed(args, resolved)
    normalized = await _execute_probe_request(
        request,
        api_dialect=resolved.connection.api_dialect,
        print_response=args.print_response,
        stream=args.stream,
    )
    print(
        json.dumps(
            {
                "profile_id": resolved.profile_id,
                "provider": resolved.provider,
                "model_name": resolved.model_name,
                "probe_kind": "text_probe",
                "stream": args.stream,
                **serialize_probe_response(normalized),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


async def _probe_tool_conformance_profile(args: argparse.Namespace, resolved, *, probe_kind: str) -> int:
    initial_request = _maybe_build_stream_request(
        build_conformance_probe_request(
            resolved.connection,
            model_name=resolved.model_name,
            probe_kind=probe_kind,
        ),
        api_dialect=resolved.connection.api_dialect,
        stream=args.stream,
    )
    if args.show_request or args.dry_run:
        print(_render_staged_request("initial", initial_request))
    if args.dry_run:
        return 0
    _enforce_rate_limit_if_needed(args, resolved)
    try:
        initial_response = await _execute_probe_request(
            initial_request,
            api_dialect=resolved.connection.api_dialect,
            print_response=args.print_response,
            stream=args.stream,
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
            "stream": args.stream,
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
            "stream": args.stream,
            "initial": serialize_probe_response(initial_response),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    result_echo = build_tool_continuation_probe_result_echo()
    try:
        followup_request = _maybe_build_stream_request(
            build_tool_continuation_probe_followup_request(
                resolved.connection,
                model_name=resolved.model_name,
                initial_response=initial_response,
                result_echo=result_echo,
            ),
            api_dialect=resolved.connection.api_dialect,
            stream=args.stream,
        )
    except ConfigurationError as exc:
        raise ConfigurationError(f"{probe_kind} follow-up request build failed: {exc}") from exc
    if args.show_request:
        print(_render_staged_request("followup", followup_request))
    _enforce_rate_limit_if_needed(args, resolved)
    try:
        followup_response = await _execute_probe_request(
            followup_request,
            api_dialect=resolved.connection.api_dialect,
            print_response=args.print_response,
            stream=args.stream,
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
        "stream": args.stream,
        "initial": serialize_probe_response(initial_response),
        "followup": serialize_probe_response(followup_response),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _render_request(request: Any) -> str:
    payload = {
        "method": request.method,
        "url": request.url,
        "headers": _mask_headers(request.headers),
        "json_body": request.json_body,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _render_staged_request(stage: str, request: Any) -> str:
    payload = {
        "stage": stage,
        "request": json.loads(_render_request(request)),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _render_response(json_body: dict[str, Any] | None, text: str) -> str:
    payload = {
        "json_body": json_body,
        "text": text,
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


async def _execute_probe_request(
    request,
    *,
    api_dialect: str,
    print_response: bool,
    stream: bool,
):
    if not stream:
        response = await send_json_http_request(request)
        print(f"HTTP {response.status_code}")
        if print_response:
            print(_render_response(response.json_body, response.text))
        if response.status_code >= 400:
            raise ConfigurationError(f"Probe failed with HTTP {response.status_code}")
        return parse_generation_response(
            api_dialect,
            response.json_body or {},
            tool_name_aliases=request.tool_name_aliases,
        )
    return await execute_stream_probe_request(
        request,
        api_dialect=api_dialect,
        print_response=print_response,
    )


def _ensure_conformance_probe_args(args: argparse.Namespace, probe_kind: str) -> None:
    if args.prompt is not None or args.system_prompt is not None:
        raise ConfigurationError(
            f"--prompt/--system-prompt 只支持 text_probe；当前 probe_kind={probe_kind}"
        )


def _maybe_build_stream_request(request, *, api_dialect: str, stream: bool):
    if not stream:
        return request
    return build_stream_probe_request(
        request,
        api_dialect=api_dialect,
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
