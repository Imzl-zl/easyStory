from __future__ import annotations

from scripts.provider_interop_check import build_parser


def test_probe_parser_defaults_to_stream() -> None:
    parser = build_parser()

    args = parser.parse_args(["probe", "gpt"])

    assert args.stream is True


def test_probe_parser_allows_explicit_buffered_override() -> None:
    parser = build_parser()

    args = parser.parse_args(["probe", "gpt", "--buffered"])

    assert args.stream is False
