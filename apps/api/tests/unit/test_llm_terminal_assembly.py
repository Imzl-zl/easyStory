from __future__ import annotations

from app.shared.runtime.llm.llm_protocol import NormalizedLLMResponse, parse_generation_response
from app.shared.runtime.llm.llm_terminal_assembly import build_stream_completion


def test_build_stream_completion_preserves_terminal_whitespace() -> None:
    normalized = build_stream_completion(
        api_dialect="openai_responses",
        text_parts=[],
        terminal_response=NormalizedLLMResponse(
            content="  保留前后空白\n",
            finish_reason="stop",
            input_tokens=1,
            output_tokens=1,
            total_tokens=2,
        ),
    )

    assert normalized is not None
    assert normalized.content == "  保留前后空白\n"


def test_parse_generation_response_preserves_whitespace_only_output_text() -> None:
    normalized = parse_generation_response(
        "openai_responses",
        {
            "id": "resp_123",
            "output_text": "  \n",
            "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
        },
    )

    assert normalized.content == "  \n"
