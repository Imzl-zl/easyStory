from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy.orm import Session

from app.modules.config_registry.infrastructure.config_loader import ConfigLoader
from app.modules.context.engine import ContextBuilder, ContextSection, create_context_builder
from app.modules.content.models import Content, ContentVersion
from tests.unit.async_service_support import async_db

PROJECT_ROOT = Path(__file__).resolve().parents[4]
API_ROOT = Path(__file__).resolve().parents[2]
CONFIG_ROOT = PROJECT_ROOT / "config"


def chapter_context_rules():
    workflow = ConfigLoader(CONFIG_ROOT).load_workflow("workflow.xuanhuan_manual")
    return create_context_builder().merge_rules(
        workflow.context_injection.default_inject,
        workflow.context_injection.rules,
        "chapter_gen",
        [],
    )


def build_context(
    builder: ContextBuilder,
    db: Session,
    project_id,
    *,
    chapter_number: int | None = None,
    workflow_execution_id=None,
    model: str = "gpt-4o",
    budget_limit: int | None = None,
    referenced_variables=None,
    rules=None,
):
    resolved_rules = chapter_context_rules() if rules is None else rules
    return asyncio.run(
        builder.build_context(
            project_id,
            resolved_rules,
            async_db(db),
            chapter_number=chapter_number,
            workflow_execution_id=workflow_execution_id,
            model=model,
            budget_limit=budget_limit,
            referenced_variables=referenced_variables,
        )
    )


def create_content_with_version(
    db: Session,
    project_id,
    content_type: str,
    title: str,
    text: str,
    *,
    chapter_number: int | None = None,
    status: str = "approved",
) -> ContentVersion:
    content = Content(
        project_id=project_id,
        content_type=content_type,
        title=title,
        chapter_number=chapter_number,
        status=status,
    )
    db.add(content)
    db.commit()
    db.refresh(content)
    version = ContentVersion(
        content_id=content.id,
        version_number=1,
        content_text=text,
        is_current=True,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def make_section(
    builder: ContextBuilder,
    inject_type: str,
    text_length: int,
    priority: int,
    min_tokens: int,
    required: bool,
) -> ContextSection:
    content = "x" * text_length
    return ContextSection(
        inject_type=inject_type,
        variable_name=inject_type,
        content=content,
        priority=priority,
        min_tokens=min_tokens,
        required=required,
        token_count=builder.token_counter.count(content, "gpt-4o"),
    )
