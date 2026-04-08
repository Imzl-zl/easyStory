from __future__ import annotations

from app.shared.runtime.llm.interop.tool_continuation_codec import (
    build_openai_responses_input,
    build_prompt_with_continuation,
    collect_continuation_tool_names,
    project_continuation_to_gemini_contents,
)
from app.shared.runtime.llm.llm_protocol_types import LLMConnection, LLMGenerateRequest


def test_build_prompt_with_continuation_renders_tool_projection_with_alias() -> None:
    prompt = build_prompt_with_continuation(
        LLMGenerateRequest(
            connection=LLMConnection(
                api_dialect="openai_chat_completions",
                api_key="test-key",
                base_url="https://api.openai.com",
            ),
            model_name="gpt-4o-mini",
            prompt="继续处理。",
            system_prompt=None,
            response_format="text",
            temperature=None,
            max_tokens=None,
            top_p=None,
            continuation_items=[
                {
                    "item_type": "tool_call",
                    "call_id": "call_123",
                    "payload": {
                        "tool_name": "project.read_documents",
                        "arguments": {"paths": ["设定/人物.md"]},
                        "tool_call_id": "call_123",
                    },
                },
                {
                    "item_type": "tool_result",
                    "call_id": "call_123",
                    "status": "completed",
                    "payload": {
                        "tool_name": "project.read_documents",
                        "content_items": [{"type": "text", "text": "设定/人物.md\n\n林渊"}],
                    },
                },
            ],
        ),
        tool_name_aliases={"project.read_documents": "project_read_documents"},
        tool_name_policy="safe_ascii_only",
    )

    assert "继续处理。" in prompt
    assert "名称：project_read_documents" in prompt
    assert "林渊" in prompt


def test_build_openai_responses_input_prefers_provider_continuation_tool_outputs() -> None:
    request = LLMGenerateRequest(
        connection=LLMConnection(
            api_dialect="openai_responses",
            api_key="test-key",
            base_url="https://api.openai.com",
        ),
        model_name="gpt-4o-mini",
        prompt="继续。",
        system_prompt=None,
        response_format="text",
        temperature=None,
        max_tokens=None,
        top_p=None,
        continuation_items=[],
        provider_continuation_state={
            "previous_response_id": "resp_prev_123",
            "latest_items": [
                {
                    "item_type": "tool_result",
                    "call_id": "call_123",
                    "payload": {
                        "structured_output": {
                            "documents": [{"path": "设定/人物.md"}],
                            "errors": [],
                        }
                    },
                }
            ],
        },
    )

    input_items = build_openai_responses_input(
        request,
        tool_name_aliases={},
        tool_name_policy="safe_ascii_only",
    )

    assert input_items == [
        {
            "type": "function_call_output",
            "call_id": "call_123",
            "output": '{"documents":[{"path":"设定/人物.md"}],"errors":[]}',
        }
    ]


def test_project_continuation_to_gemini_contents_preserves_call_result_pair() -> None:
    contents = project_continuation_to_gemini_contents(
        [
            {
                "item_type": "tool_call",
                "call_id": "call_123",
                "payload": {
                    "tool_name": "project.read_documents",
                    "arguments": {"paths": ["设定/人物.md"]},
                    "tool_call_id": "call_123",
                },
            },
            {
                "item_type": "tool_result",
                "call_id": "call_123",
                "status": "completed",
                "payload": {
                    "content_items": [{"type": "text", "text": "设定/人物.md\n\n林渊"}],
                },
            },
        ],
        tool_name_aliases={"project.read_documents": "project_read_documents"},
        tool_name_policy="safe_ascii_only",
    )

    assert contents[0]["parts"][0]["functionCall"]["name"] == "project_read_documents"
    assert contents[1]["parts"][0]["functionResponse"]["name"] == "project_read_documents"
    assert contents[1]["parts"][0]["functionResponse"]["response"]["status"] == "completed"


def test_collect_continuation_tool_names_reads_tool_call_and_tool_result_names() -> None:
    names = collect_continuation_tool_names(
        [
            {
                "item_type": "tool_call",
                "payload": {"tool_name": "project.search_documents"},
            },
            {
                "item_type": "tool_result",
                "payload": {"tool_name": "project.read_documents"},
            },
            {
                "item_type": "tool_result",
                "tool_name": "project.write_document",
                "payload": {},
            },
        ]
    )

    assert names == [
        "project.search_documents",
        "project.read_documents",
        "project.write_document",
    ]
