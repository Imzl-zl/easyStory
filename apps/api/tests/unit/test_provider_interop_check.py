from __future__ import annotations

from scripts.provider_interop_check import build_parser


def test_probe_parser_defaults_to_stream() -> None:
    parser = build_parser()

    args = parser.parse_args(["probe", "gpt"])

    assert args.stream is True
    assert args.probe_kind == "text_probe"


def test_probe_parser_allows_explicit_buffered_override() -> None:
    parser = build_parser()

    args = parser.parse_args(["probe", "gpt", "--buffered"])

    assert args.stream is False


def test_probe_parser_accepts_tool_continuation_probe_kind() -> None:
    parser = build_parser()

    args = parser.parse_args(["probe", "gpt", "--probe-kind", "tool_continuation_probe"])

    assert args.probe_kind == "tool_continuation_probe"
