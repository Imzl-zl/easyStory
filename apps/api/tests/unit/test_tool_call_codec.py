from __future__ import annotations

import pytest

from app.shared.runtime.errors import ConfigurationError
from app.shared.runtime.llm.interop.tool_call_codec import (
    build_tool_call,
    extract_anthropic_tool_calls,
    extract_gemini_tool_calls,
    extract_openai_chat_tool_calls,
    extract_openai_responses_tool_calls,
    parse_tool_arguments,
)


def test_extract_openai_chat_tool_calls_decodes_alias_and_parses_arguments() -> None:
    tool_calls = extract_openai_chat_tool_calls(
        {
            "tool_calls": [
                {
                    "id": "call_123",
                    "function": {
                        "name": "project_read_documents",
                        "arguments": '{"paths":["设定/人物.md"]}',
                    },
                }
            ]
        },
        tool_name_aliases={"project.read_documents": "project_read_documents"},
    )

    assert tool_calls[0].tool_call_id == "call_123"
    assert tool_calls[0].tool_name == "project.read_documents"
    assert tool_calls[0].arguments == {"paths": ["设定/人物.md"]}


def test_extract_openai_responses_tool_calls_preserves_provider_ref_and_invalid_arguments() -> None:
    tool_calls = extract_openai_responses_tool_calls(
        [
            {
                "id": "fc_123",
                "type": "function_call",
                "call_id": "call_123",
                "name": "project_read_documents",
                "arguments": '{"paths":["设定/人物.md"]',
            }
        ],
        tool_name_aliases={"project.read_documents": "project_read_documents"},
    )

    assert tool_calls[0].provider_ref == "fc_123"
    assert tool_calls[0].tool_name == "project.read_documents"
    assert tool_calls[0].arguments == {}
    assert tool_calls[0].arguments_text == '{"paths":["设定/人物.md"]'
    assert tool_calls[0].arguments_error == "Tool call arguments JSON is invalid"


def test_extract_anthropic_tool_calls_keeps_structured_input() -> None:
    tool_calls = extract_anthropic_tool_calls(
        [
            {
                "type": "tool_use",
                "id": "toolu_123",
                "name": "project_read_documents",
                "input": {"paths": ["设定/人物.md"]},
            }
        ],
        tool_name_aliases={"project.read_documents": "project_read_documents"},
    )

    assert tool_calls[0].tool_call_id == "toolu_123"
    assert tool_calls[0].tool_name == "project.read_documents"
    assert tool_calls[0].arguments_text == '{"paths":["设定/人物.md"]}'


def test_extract_gemini_tool_calls_generates_fallback_tool_call_id() -> None:
    tool_calls = extract_gemini_tool_calls(
        [
            {
                "functionCall": {
                    "name": "project_read_documents",
                    "args": {"paths": ["设定/人物.md"]},
                }
            }
        ],
        tool_name_aliases={"project.read_documents": "project_read_documents"},
    )

    assert tool_calls[0].tool_call_id == "provider:gemini_generate_content:tool_call:1"
    assert tool_calls[0].tool_name == "project.read_documents"


@pytest.mark.parametrize(
    ("raw_arguments", "expected_error"),
    [
        ('["not-an-object"]', "Tool call arguments JSON must decode to an object"),
        (123, "Tool call arguments must be an object or JSON string"),
    ],
)
def test_parse_tool_arguments_surfaces_invalid_contracts(
    raw_arguments: object,
    expected_error: str,
) -> None:
    parsed, arguments_text, arguments_error = parse_tool_arguments(raw_arguments)

    assert parsed == {}
    assert arguments_error == expected_error
    if isinstance(raw_arguments, str):
        assert arguments_text == raw_arguments
    else:
        assert arguments_text is None


def test_build_tool_call_requires_id_and_name() -> None:
    with pytest.raises(ConfigurationError, match="Tool call is missing id"):
        build_tool_call(
            tool_call_id=None,
            tool_name="project.read_documents",
            arguments=({}, None, None),
        )

    with pytest.raises(ConfigurationError, match="Tool call is missing name"):
        build_tool_call(
            tool_call_id="call_123",
            tool_name=None,
            arguments=({}, None, None),
        )
