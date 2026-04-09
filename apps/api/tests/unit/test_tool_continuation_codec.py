from __future__ import annotations

import json

from app.shared.runtime.llm.interop.tool_continuation_codec import (
    build_openai_responses_input,
    build_prompt_with_continuation,
    collect_continuation_tool_names,
    project_continuation_to_anthropic_messages,
    project_continuation_to_gemini_contents,
    project_continuation_to_openai_chat_messages,
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
    assert prompt.index("继续处理。") < prompt.index("【工具调用】")


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


def test_project_continuation_to_gemini_contents_preserves_provider_tool_metadata() -> None:
    contents = project_continuation_to_gemini_contents(
        [
            {
                "item_type": "tool_call",
                "call_id": "call_123",
                "payload": {
                    "tool_name": "project.read_documents",
                    "arguments": {"paths": ["设定/人物.md"]},
                    "tool_call_id": "call_123",
                    "provider_payload": {
                        "thoughtSignature": "sig_123",
                        "functionCall": {
                            "id": "fn_123",
                            "name": "project_read_documents",
                            "args": {"paths": ["设定/人物.md"]},
                        },
                    },
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

    assert contents[0]["parts"][0]["thoughtSignature"] == "sig_123"
    assert contents[0]["parts"][0]["functionCall"]["id"] == "fn_123"
    assert contents[1]["parts"][0]["functionResponse"]["id"] == "fn_123"


def test_project_continuation_to_gemini_contents_groups_parallel_tool_step() -> None:
    contents = project_continuation_to_gemini_contents(
        [
            {
                "item_type": "tool_call",
                "call_id": "call_123",
                "tool_cycle_index": 0,
                "payload": {
                    "tool_name": "project.read_documents",
                    "arguments": {"paths": ["设定/人物-1.md"]},
                    "tool_call_id": "call_123",
                    "provider_payload": {
                        "thoughtSignature": "sig_parallel",
                        "functionCall": {
                            "id": "fn_123",
                            "name": "project_read_documents",
                            "args": {"paths": ["设定/人物-1.md"]},
                        },
                    },
                },
            },
            {
                "item_type": "tool_result",
                "call_id": "call_123",
                "status": "completed",
                "tool_cycle_index": 0,
                "payload": {
                    "content_items": [{"type": "text", "text": "设定/人物-1.md\n\n林渊"}],
                },
            },
            {
                "item_type": "tool_call",
                "call_id": "call_456",
                "tool_cycle_index": 0,
                "payload": {
                    "tool_name": "project.read_documents",
                    "arguments": {"paths": ["设定/人物-2.md"]},
                    "tool_call_id": "call_456",
                    "provider_payload": {
                        "functionCall": {
                            "id": "fn_456",
                            "name": "project_read_documents",
                            "args": {"paths": ["设定/人物-2.md"]},
                        },
                    },
                },
            },
            {
                "item_type": "tool_result",
                "call_id": "call_456",
                "status": "completed",
                "tool_cycle_index": 0,
                "payload": {
                    "content_items": [{"type": "text", "text": "设定/人物-2.md\n\n顾砚"}],
                },
            },
        ],
        tool_name_aliases={"project.read_documents": "project_read_documents"},
        tool_name_policy="safe_ascii_only",
    )

    assert [item["role"] for item in contents] == ["model", "user"]
    assert len(contents[0]["parts"]) == 2
    assert contents[0]["parts"][0]["thoughtSignature"] == "sig_parallel"
    assert contents[0]["parts"][0]["functionCall"]["id"] == "fn_123"
    assert contents[0]["parts"][1]["functionCall"]["id"] == "fn_456"
    assert len(contents[1]["parts"]) == 2
    assert [part["functionResponse"]["id"] for part in contents[1]["parts"]] == [
        "fn_123",
        "fn_456",
    ]


def test_project_continuation_to_openai_chat_messages_strips_internal_tool_result_metadata() -> None:
    messages = project_continuation_to_openai_chat_messages(
        [
            {
                "item_type": "tool_result",
                "call_id": "call_123",
                "tool_name": "project.read_documents",
                "status": "completed",
                "tool_cycle_index": 3,
                "payload": {
                    "tool_name": "project.read_documents",
                    "tool_call_id": "call_123",
                    "structured_output": {"documents": [{"path": "设定/人物.md"}]},
                    "content_items": [{"type": "text", "text": "设定/人物.md\n\n林渊"}],
                    "resource_links": [],
                    "error": None,
                    "audit": {"run_audit_id": "audit-1"},
                    "tool_cycle_index": 3,
                },
            }
        ],
        tool_name_aliases={"project.read_documents": "project_read_documents"},
        tool_name_policy="safe_ascii_only",
    )

    payload = json.loads(messages[0]["content"])

    assert "audit" not in payload
    assert "tool_cycle_index" not in payload
    assert "tool_call_id" not in payload
    assert payload["tool_name"] == "project_read_documents"


def test_project_continuation_to_anthropic_messages_strips_internal_tool_result_metadata() -> None:
    messages = project_continuation_to_anthropic_messages(
        [
            {
                "item_type": "tool_result",
                "call_id": "call_123",
                "tool_name": "project.read_documents",
                "status": "completed",
                "tool_cycle_index": 3,
                "payload": {
                    "tool_name": "project.read_documents",
                    "tool_call_id": "call_123",
                    "structured_output": {"documents": [{"path": "设定/人物.md"}]},
                    "content_items": [{"type": "text", "text": "设定/人物.md\n\n林渊"}],
                    "resource_links": [],
                    "error": None,
                    "audit": {"run_audit_id": "audit-1"},
                    "tool_cycle_index": 3,
                },
            }
        ],
        tool_name_aliases={"project.read_documents": "project_read_documents"},
        tool_name_policy="safe_ascii_only",
    )

    payload = json.loads(messages[0]["content"][0]["content"])

    assert "audit" not in payload
    assert "tool_cycle_index" not in payload
    assert "tool_call_id" not in payload
    assert payload["tool_name"] == "project_read_documents"


def test_project_continuation_to_gemini_contents_strips_internal_tool_result_metadata() -> None:
    contents = project_continuation_to_gemini_contents(
        [
            {
                "item_type": "tool_call",
                "call_id": "call_123",
                "payload": {
                    "tool_name": "project.read_documents",
                    "arguments": {"paths": ["设定/人物.md"]},
                    "tool_call_id": "call_123",
                    "provider_payload": {
                        "thoughtSignature": "sig_123",
                        "functionCall": {
                            "id": "fn_123",
                            "name": "project_read_documents",
                            "args": {"paths": ["设定/人物.md"]},
                        },
                    },
                },
            },
            {
                "item_type": "tool_result",
                "call_id": "call_123",
                "tool_name": "project.read_documents",
                "status": "completed",
                "tool_cycle_index": 2,
                "payload": {
                    "tool_name": "project.read_documents",
                    "tool_call_id": "call_123",
                    "structured_output": {"documents": [{"path": "设定/人物.md"}]},
                    "content_items": [{"type": "text", "text": "设定/人物.md\n\n林渊"}],
                    "resource_links": [],
                    "error": None,
                    "audit": {"run_audit_id": "audit-1"},
                    "tool_cycle_index": 2,
                },
            },
        ],
        tool_name_aliases={"project.read_documents": "project_read_documents"},
        tool_name_policy="safe_ascii_only",
    )

    response_payload = contents[1]["parts"][0]["functionResponse"]["response"]

    assert "audit" not in response_payload
    assert "tool_cycle_index" not in response_payload
    assert "tool_call_id" not in response_payload
    assert contents[1]["parts"][0]["functionResponse"]["id"] == "fn_123"


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
