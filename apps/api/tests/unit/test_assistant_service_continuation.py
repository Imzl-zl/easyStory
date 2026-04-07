from __future__ import annotations

import json

from app.modules.assistant.service.assistant_config_file_store import AssistantConfigFileStore
from app.modules.assistant.service.assistant_service import AssistantService
from app.modules.assistant.service.tooling.assistant_tool_executor import AssistantToolExecutor
from app.modules.assistant.service.tooling.assistant_tool_exposure_policy import AssistantToolExposurePolicy
from app.modules.assistant.service.tooling.assistant_tool_loop import AssistantToolLoop
from app.modules.assistant.service.tooling.assistant_tool_registry import AssistantToolDescriptorRegistry
from app.modules.assistant.service.tooling.assistant_tool_step_store import AssistantToolStepStore
from app.modules.assistant.service.dto import AssistantMessageDTO
from app.modules.assistant.service.factory import create_assistant_rule_service
from app.modules.config_registry import ConfigLoader
from app.modules.project.infrastructure import ProjectDocumentFileStore, ProjectDocumentIdentityStore
from app.modules.project.service import ProjectDocumentCapabilityService, ProjectService
from app.shared.runtime import LLMToolProvider, SkillTemplateRenderer
from app.shared.runtime.llm_protocol import HttpJsonResponse
from tests.unit.assistant_service_test_support import (
    _AnthropicCredentialService,
    _AnthropicToolLoopRequestSender,
    _FakeCredentialService,
    _build_config_root,
    _build_turn_request,
)
from tests.unit.async_service_support import async_db
from tests.unit.models.helpers import create_project, create_user


async def test_assistant_service_uses_runtime_replay_for_anthropic_tool_loop(db, tmp_path) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    request_sender = _AnthropicToolLoopRequestSender()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    registry = AssistantToolDescriptorRegistry()
    exposure_policy = AssistantToolExposurePolicy(registry=registry)
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)
    step_store = AssistantToolStepStore(tmp_path / "tool-steps")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_AnthropicCredentialService,
        project_service=project_service,
        tool_provider=LLMToolProvider(request_sender=request_sender),
        template_renderer=SkillTemplateRenderer(),
        assistant_tool_descriptor_registry=registry,
        assistant_tool_exposure_policy=exposure_policy,
        assistant_tool_executor=executor,
        assistant_tool_loop=AssistantToolLoop(
            exposure_policy=exposure_policy,
            executor=executor,
            step_store=step_store,
        ),
    )
    owner = create_user(db)
    project = create_project(db, owner=owner)
    file_store.save_project_document(
        project.id,
        "设定/人物.md",
        "# 人物\n\n林渊：冷静、克制，擅长从细枝末节里发现异常。",
    )
    payload = _build_turn_request(
        project_id=project.id,
        model={"provider": "anthropic", "name": "claude-sonnet-4-20250514"},
        messages=[AssistantMessageDTO(role="user", content="先读一下人物设定，再给我一个悬疑开场方向。")],
    )

    response = await service.turn(async_db(db), payload, owner_id=owner.id)

    assert response.content == "我已经读完人物设定，可以继续。"
    assert len(request_sender.requests) == 2
    second_request = request_sender.requests[1]
    assert "previous_response_id" not in second_request.json_body
    assert (
        second_request.json_body["messages"][0]["content"][0]["text"]
        == "【用户当前消息】\n先读一下人物设定，再给我一个悬疑开场方向。"
    )
    assert second_request.json_body["messages"][1]["content"][0]["type"] == "tool_use"
    assert second_request.json_body["messages"][2]["content"][0]["type"] == "tool_result"
    assert "设定/人物.md" in second_request.json_body["messages"][2]["content"][0]["content"]
    step_history = step_store.list_step_history(response.run_id, "call.project.read_documents.1")
    assert [item.status for item in step_history] == ["reading", "completed"]


class _InvalidToolArgumentsRequestSender:
    def __init__(self) -> None:
        self.requests: list[object] = []

    async def __call__(self, request) -> HttpJsonResponse:
        self.requests.append(request)
        if len(self.requests) == 1:
            return HttpJsonResponse(
                status_code=200,
                json_body={
                    "id": "resp_bad_1",
                    "output": [
                        {
                            "id": "fc_bad",
                            "type": "function_call",
                            "call_id": "call.project.read_documents.bad",
                            "name": "project.read_documents",
                            "arguments": '{"paths":["设定/人物.md"]',
                        }
                    ],
                    "usage": {
                        "input_tokens": 12,
                        "output_tokens": 4,
                        "total_tokens": 16,
                    },
                },
                text="",
            )
        return HttpJsonResponse(
            status_code=200,
            json_body={
                "id": "resp_bad_2",
                "output_text": "工具参数格式不合法，我会重新组织调用。",
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 6,
                    "total_tokens": 16,
                },
            },
            text="",
        )


async def test_assistant_service_returns_invalid_arguments_to_model_when_provider_tool_args_are_malformed(
    db,
    tmp_path,
) -> None:
    config_root = _build_config_root(tmp_path)
    loader = ConfigLoader(config_root)
    request_sender = _InvalidToolArgumentsRequestSender()
    assistant_store = AssistantConfigFileStore(tmp_path / "assistant-config")
    document_root = tmp_path / "project-documents"
    file_store = ProjectDocumentFileStore(document_root)
    identity_store = ProjectDocumentIdentityStore(document_root)
    project_service = ProjectService(
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    capability_service = ProjectDocumentCapabilityService(
        project_service=project_service,
        document_file_store=file_store,
        document_identity_store=identity_store,
    )
    registry = AssistantToolDescriptorRegistry()
    exposure_policy = AssistantToolExposurePolicy(registry=registry)
    executor = AssistantToolExecutor(project_document_capability_service=capability_service)
    step_store = AssistantToolStepStore(tmp_path / "tool-steps")
    service = AssistantService(
        assistant_rule_service=create_assistant_rule_service(config_store=assistant_store),
        config_loader=loader,
        credential_service_factory=_FakeCredentialService,
        project_service=project_service,
        tool_provider=LLMToolProvider(request_sender=request_sender),
        template_renderer=SkillTemplateRenderer(),
        assistant_tool_descriptor_registry=registry,
        assistant_tool_exposure_policy=exposure_policy,
        assistant_tool_executor=executor,
        assistant_tool_loop=AssistantToolLoop(
            exposure_policy=exposure_policy,
            executor=executor,
            step_store=step_store,
        ),
    )
    owner = create_user(db)
    project = create_project(db, owner=owner)
    payload = _build_turn_request(
        project_id=project.id,
        model={"provider": "openai", "name": "gpt-4o-mini"},
        messages=[AssistantMessageDTO(role="user", content="先读一下人物设定，再继续。")],
    )

    response = await service.turn(async_db(db), payload, owner_id=owner.id)

    assert response.content == "工具参数格式不合法，我会重新组织调用。"
    assert len(request_sender.requests) == 2
    second_request_payload = json.dumps(request_sender.requests[1].json_body, ensure_ascii=False)
    assert "invalid_arguments" in second_request_payload
    assert "Tool call arguments JSON is invalid" in second_request_payload
    step_history = step_store.list_step_history(
        response.run_id,
        "call.project.read_documents.bad",
    )
    assert [item.status for item in step_history] == ["reading", "failed"]
    assert step_history[-1].error_code == "invalid_arguments"
