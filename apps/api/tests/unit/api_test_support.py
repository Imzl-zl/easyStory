from __future__ import annotations

import asyncio
import threading
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker

from app.main import create_app
from app.modules.billing.service import create_billing_service
from app.modules.content.models import Content, ContentVersion
from app.modules.content.service import create_chapter_content_service
from app.modules.context.engine import create_context_builder
from app.modules.credential.models import ModelCredential
from app.modules.export.entry.http.router import get_export_service
from app.modules.export.service import ExportService, create_export_service
from app.modules.user.service import TokenService
from app.modules.workflow.entry.http.router import (
    get_workflow_app_service,
    get_workflow_runtime_dispatcher,
)
from app.modules.workflow.service import (
    WorkflowRuntimeService,
    create_workflow_app_service,
    create_workflow_service,
)
from app.shared.runtime import SkillTemplateRenderer, ToolProvider
from tests.unit.models.helpers import create_project, create_template, create_user, ready_project_setting

TEST_JWT_SECRET = "test-jwt-secret"


def auth_headers(user_id: uuid.UUID) -> dict[str, str]:
    token = TokenService().issue_for_user(user_id)
    return {"Authorization": f"Bearer {token}"}


def seed_workflow_project(
    session_factory: sessionmaker[Session],
    *,
    ready_assets: bool,
) -> tuple[str, uuid.UUID]:
    with session_factory() as session:
        owner = create_user(session)
        template = create_template(session)
        project = create_project(
            session,
            owner=owner,
            template_id=template.id,
            project_setting=ready_project_setting(),
        )
        if ready_assets:
            _create_asset(session, project.id, "outline", "大纲")
            _create_asset(session, project.id, "opening_plan", "开篇设计")
        return str(project.id), owner.id


def build_runtime_app(
    session_factory,
    async_session_factory,
    *,
    export_root: Path | None = None,
    runtime_dispatcher=None,
):
    app = create_app(
        async_session_factory=async_session_factory,
    )
    workflow_service = create_workflow_service()
    export_service = ExportService(export_root or (Path.cwd() / ".pytest-exports"))
    runtime_service = WorkflowRuntimeService(
        workflow_service=workflow_service,
        billing_service=create_billing_service(),
        chapter_content_service=create_chapter_content_service(),
        context_builder=create_context_builder(),
        credential_service_factory=lambda: _FakeCredentialService(),
        export_service=export_service,
        template_renderer=SkillTemplateRenderer(),
        tool_provider=_FakeToolProvider(),
    )
    workflow_app_service = create_workflow_app_service(
        workflow_service=workflow_service,
        runtime_service=runtime_service,
    )
    dispatcher = runtime_dispatcher or _InlineWorkflowDispatcher(
        async_session_factory,
        workflow_app_service,
    )
    app.dependency_overrides[get_workflow_app_service] = lambda: workflow_app_service
    app.dependency_overrides[get_workflow_runtime_dispatcher] = lambda: dispatcher
    app.dependency_overrides[get_export_service] = lambda: create_export_service(
        export_root=export_service.export_root
    )
    return app


class NoopWorkflowDispatcher:
    def __init__(self) -> None:
        self.calls: list[tuple[uuid.UUID, uuid.UUID]] = []

    def __call__(self, workflow_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        self.calls.append((workflow_id, owner_id))


def _create_asset(
    session: Session,
    project_id: uuid.UUID,
    content_type: str,
    title: str,
) -> None:
    content = Content(
        project_id=project_id,
        content_type=content_type,
        title=title,
        status="approved",
    )
    session.add(content)
    session.flush()
    session.add(
        ContentVersion(
            content_id=content.id,
            version_number=1,
            content_text=f"{title}内容",
            is_current=True,
        )
    )
    session.commit()


class _FakeCrypto:
    def decrypt(self, value: str) -> str:
        return value


class _FakeCredentialService:
    def __init__(self) -> None:
        self.crypto = _FakeCrypto()

    async def resolve_active_credential(
        self,
        db: AsyncSession,
        *,
        provider: str,
        user_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
    ) -> ModelCredential:
        del project_id
        statement = select(ModelCredential).where(
            ModelCredential.owner_type == "user",
            ModelCredential.owner_id == user_id,
            ModelCredential.provider == provider,
        )
        credential = await db.scalar(statement)
        if credential is None:
            credential = ModelCredential(
                owner_type="user",
                owner_id=user_id,
                provider=provider,
                display_name=f"{provider}-fake",
                encrypted_key=f"{provider}-fake-key",
                is_active=True,
            )
            db.add(credential)
            await db.flush()
        return credential


class _FakeToolProvider(ToolProvider):
    async def execute(self, tool_name: str, params: dict) -> dict:
        assert tool_name == "llm.generate"
        prompt = params["prompt"]
        if "请拆分出可执行的章节任务列表" in prompt:
            return {
                "content": {
                    "chapters": [
                        {
                            "chapter_number": 1,
                            "title": "第一章 逃亡夜",
                            "brief": "主角连夜出逃并暴露追兵",
                            "key_characters": ["林渊"],
                            "key_events": ["夜逃"],
                        },
                        {
                            "chapter_number": 2,
                            "title": "第二章 山门截杀",
                            "brief": "主角在山门外首次反杀",
                            "key_characters": ["林渊"],
                            "key_events": ["反杀"],
                        },
                    ]
                },
                "input_tokens": 10,
                "output_tokens": 20,
                "total_tokens": 30,
            }
        if "输出一个严格符合 ReviewResult 的 JSON 对象" in prompt:
            return {
                "content": {
                    "reviewer_id": "agent.style_checker",
                    "reviewer_name": "文风检查员",
                    "status": "passed",
                    "score": 92,
                    "issues": [],
                    "summary": "通过",
                    "execution_time_ms": 1,
                    "tokens_used": 10,
                },
                "input_tokens": 8,
                "output_tokens": 8,
                "total_tokens": 16,
            }
        if "第二章 山门截杀" in prompt:
            return {
                "content": "第二章正文：山门外的反杀正式展开。",
                "input_tokens": 15,
                "output_tokens": 40,
                "total_tokens": 55,
            }
        return {
            "content": "第一章正文：林渊在夜色中踏上逃亡之路。",
            "input_tokens": 12,
            "output_tokens": 36,
            "total_tokens": 48,
        }

    def list_tools(self) -> list[str]:
        return ["llm.generate"]


class _InlineWorkflowDispatcher:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        workflow_app_service,
    ) -> None:
        self.session_factory = session_factory
        self.workflow_app_service = workflow_app_service

    def __call__(self, workflow_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        error: BaseException | None = None

        def run() -> None:
            nonlocal error
            try:
                asyncio.run(self._run_runtime(workflow_id, owner_id))
            except BaseException as exc:  # pragma: no cover
                error = exc

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        thread.join()
        if error is not None:
            raise error

    async def _run_runtime(self, workflow_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        async with self.session_factory() as session:
            await self.workflow_app_service.run_workflow_runtime(
                session,
                workflow_id,
                owner_id=owner_id,
            )
