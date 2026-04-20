from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import uuid

from app.modules.assistant.service.dto import AssistantTurnRequestDTO
from app.modules.credential.models import ModelCredential
from app.shared.runtime.llm.llm_protocol_types import HttpJsonResponse


class _FakeCrypto:
    def decrypt(self, value: str) -> str:
        return value


@dataclass(frozen=True)
class _ResolvedCredentialModel:
    credential: ModelCredential
    model_name: str


class _FakeCredentialService:
    def __init__(self) -> None:
        self.crypto = _FakeCrypto()

    async def resolve_active_credential(self, db, *, provider: str, user_id, project_id=None):
        del db, user_id, project_id
        api_dialect = "openai_responses"
        default_model = "gpt-4o-mini"
        interop_profile = "responses_strict"
        if provider == "gemini":
            api_dialect = "gemini_generate_content"
            default_model = "gemini-2.5-flash"
            interop_profile = None
        elif provider == "anthropic":
            api_dialect = "anthropic_messages"
            default_model = "claude-sonnet-4-20250514"
            interop_profile = None
        return ModelCredential(
            owner_type="user",
            owner_id=uuid.uuid4(),
            provider=provider,
            display_name=f"{provider}-test",
            encrypted_key=f"{provider}-key",
            api_dialect=api_dialect,
            default_model=default_model,
            interop_profile=interop_profile,
            stream_tool_verified_probe_kind="tool_continuation_probe",
            buffered_tool_verified_probe_kind="tool_continuation_probe",
            is_active=True,
        )

    async def resolve_active_credential_model(
        self,
        db,
        *,
        provider: str,
        requested_model_name: str | None,
        user_id,
        project_id=None,
    ):
        credential = await self.resolve_active_credential(
            db,
            provider=provider,
            user_id=user_id,
            project_id=project_id,
        )
        return _ResolvedCredentialModel(
            credential=credential,
            model_name=requested_model_name or credential.default_model or "",
        )


class _AnthropicCredentialService(_FakeCredentialService):
    async def resolve_active_credential(self, db, *, provider: str, user_id, project_id=None):
        del db, user_id, project_id
        return ModelCredential(
            owner_type="user",
            owner_id=uuid.uuid4(),
            provider=provider,
            display_name=f"{provider}-test",
            encrypted_key=f"{provider}-key",
            api_dialect="anthropic_messages",
            default_model="claude-sonnet-4-20250514",
            stream_tool_verified_probe_kind="tool_continuation_probe",
            buffered_tool_verified_probe_kind="tool_continuation_probe",
            is_active=True,
        )


class _CompactingCredentialService(_FakeCredentialService):
    async def resolve_active_credential(self, db, *, provider: str, user_id, project_id=None):
        del db, user_id, project_id
        return ModelCredential(
            owner_type="user",
            owner_id=uuid.uuid4(),
            provider=provider,
            display_name=f"{provider}-compacting-test",
            encrypted_key=f"{provider}-key",
            api_dialect="openai_responses",
            default_model="gpt-4o-mini",
            interop_profile="responses_strict",
            context_window_tokens=280,
            stream_tool_verified_probe_kind="tool_continuation_probe",
            buffered_tool_verified_probe_kind="tool_continuation_probe",
            is_active=True,
        )


class _InteropProfileCredentialService(_FakeCredentialService):
    async def resolve_active_credential(self, db, *, provider: str, user_id, project_id=None):
        del db, user_id, project_id
        return ModelCredential(
            owner_type="user",
            owner_id=uuid.uuid4(),
            provider=provider,
            display_name=f"{provider}-interop-test",
            encrypted_key=f"{provider}-key",
            api_dialect="openai_chat_completions",
            default_model="gpt-4o-mini",
            interop_profile="chat_compat_reasoning_content",
            stream_tool_verified_probe_kind="tool_continuation_probe",
            buffered_tool_verified_probe_kind="tool_continuation_probe",
            is_active=True,
        )


class _TextOnlyCredentialService(_FakeCredentialService):
    async def resolve_active_credential(self, db, *, provider: str, user_id, project_id=None):
        del db, user_id, project_id
        return ModelCredential(
            owner_type="user",
            owner_id=uuid.uuid4(),
            provider=provider,
            display_name=f"{provider}-text-only",
            encrypted_key=f"{provider}-key",
            api_dialect="openai_responses",
            default_model="gpt-4o-mini",
            interop_profile="responses_strict",
            is_active=True,
        )


class _AnthropicToolLoopRequestSender:
    def __init__(self) -> None:
        self.requests: list[object] = []

    async def __call__(self, request) -> HttpJsonResponse:
        self.requests.append(request)
        if len(self.requests) == 1:
            return HttpJsonResponse(
                status_code=200,
                json_body={
                    "id": "msg_tool_1",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "call.project.read_documents.1",
                            "name": "project.read_documents",
                            "input": {"paths": ["设定/人物.md"]},
                        }
                    ],
                    "usage": {"input_tokens": 12, "output_tokens": 4},
                    "stop_reason": "tool_use",
                },
                text="",
            )
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "id": "msg_tool_2",
                "content": [{"type": "text", "text": "我已经读完人物设定，可以继续。"}],
                "usage": {"input_tokens": 10, "output_tokens": 6},
                "stop_reason": "end_turn",
            },
            text="",
        )


def _build_turn_request(**overrides) -> AssistantTurnRequestDTO:
    payload = {
        "conversation_id": "conversation-test",
        "client_turn_id": f"turn-{uuid.uuid4()}",
        "requested_write_scope": "disabled",
    }
    payload.update(overrides)
    return AssistantTurnRequestDTO(**payload)


def _build_config_root(tmp_path: Path) -> Path:
    root = tmp_path / "config"
    _write_yaml(
        root / "skills" / "assistant" / "general-chat.yaml",
        """
skill:
  id: "skill.assistant.general_chat"
  name: "通用对话助手"
  category: "assistant"
  prompt: |
    你是一个通用助手。
    {% if conversation_history %}
    历史对话：
    {{ conversation_history }}
    {% endif %}
    用户问题：{{ user_input }}
  variables:
    conversation_history:
      type: "string"
      required: false
      default: ""
    user_input:
      type: "string"
      required: true
  model:
    provider: "openai"
    name: "gpt-4o-mini"
""",
    )
    _write_yaml(
        root / "skills" / "assistant" / "hook-summary.yaml",
        """
skill:
  id: "skill.assistant.hook_summary"
  name: "Hook 摘要"
  category: "assistant"
  prompt: |
    请根据以下内容输出一句摘要：
    {{ content }}
  variables:
    content:
      type: "string"
      required: true
  model:
    provider: "openai"
    name: "gpt-4o-mini"
""",
    )
    _write_yaml(
        root / "agents" / "writers" / "general-assistant.yaml",
        """
agent:
  id: "agent.general_assistant"
  name: "通用助手"
  type: "writer"
  system_prompt: "你是通用助手。"
  skills: ["skill.assistant.general_chat"]
  mcp_servers: ["mcp.news.lookup"]
  model:
    provider: "openai"
    name: "gpt-4o-mini"
""",
    )
    _write_yaml(
        root / "agents" / "writers" / "hook-summary.yaml",
        """
agent:
  id: "agent.hook_summary"
  name: "Hook 摘要助手"
  type: "checker"
  system_prompt: "你负责给正文做一句摘要。"
  skills: ["skill.assistant.hook_summary"]
  model:
    provider: "openai"
    name: "gpt-4o-mini"
""",
    )
    _write_yaml(
        root / "hooks" / "before-news-lookup.yaml",
        """
hook:
  id: "hook.before_news_lookup"
  name: "新闻检索"
  trigger:
    event: "before_assistant_response"
  action:
    type: "mcp"
    config:
      server_id: "mcp.news.lookup"
      tool_name: "search_news"
      input_mapping:
        query: "request.user_input"
""",
    )
    _write_yaml(
        root / "hooks" / "after-summary-agent.yaml",
        """
hook:
  id: "hook.after_summary_agent"
  name: "生成摘要"
  trigger:
    event: "after_assistant_response"
  action:
    type: "agent"
    config:
      agent_id: "agent.hook_summary"
      input_mapping:
        content: "response.content"
""",
    )
    _write_yaml(
        root / "mcp_servers" / "news.yaml",
        """
mcp_server:
  id: "mcp.news.lookup"
  name: "新闻检索 MCP"
  transport: "streamable_http"
  url: "https://example.com/mcp"
""",
    )
    return root


def _write_yaml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
