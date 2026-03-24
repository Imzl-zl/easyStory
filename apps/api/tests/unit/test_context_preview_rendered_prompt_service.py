from __future__ import annotations

import asyncio

import pytest

from app.modules.analysis.models import Analysis
from app.modules.context.engine.contracts import STYLE_REFERENCE_MAX_TOKENS
from app.shared.runtime.errors import ConfigurationError
from tests.unit.async_service_support import async_db
from tests.unit.test_context_preview_style_reference import _create_preview_workflow
from tests.unit.models.helpers import create_user
from app.modules.context.service import ContextPreviewRequestDTO, create_context_preview_service


def test_context_preview_service_rejects_rendered_prompt_when_style_reference_is_unconfigured(
    db,
) -> None:
    owner = create_user(db)
    workflow = _create_preview_workflow(db, owner=owner, inject_style_reference=False)
    service = create_context_preview_service()

    with pytest.raises(ConfigurationError, match="Context preview prompt render failed"):
        asyncio.run(
            service.preview_workflow_context(
                async_db(db),
                workflow.id,
                ContextPreviewRequestDTO(node_id="chapter_gen", chapter_number=1),
                owner_id=owner.id,
            )
        )


def test_context_preview_service_truncates_style_reference_in_rendered_prompt(db) -> None:
    owner = create_user(db)
    workflow = _create_preview_workflow(db, owner=owner, inject_style_reference=True)
    analysis = db.query(Analysis).filter(Analysis.project_id == workflow.project_id).one()
    analysis.result = {"writing_style": "凌" * 1600}
    db.add(analysis)
    db.commit()
    service = create_context_preview_service()

    preview = asyncio.run(
        service.preview_workflow_context(
            async_db(db),
            workflow.id,
            ContextPreviewRequestDTO(node_id="chapter_gen", chapter_number=1),
            owner_id=owner.id,
        )
    )

    style_reference_report = next(
        item for item in preview.context_report["sections"] if item["type"] == "style_reference"
    )
    assert style_reference_report["status"] == "truncated"
    assert style_reference_report["token_cap"] == STYLE_REFERENCE_MAX_TOKENS
    assert style_reference_report["original_tokens"] > style_reference_report["token_count"]
    assert style_reference_report["token_count"] <= STYLE_REFERENCE_MAX_TOKENS
    assert "\n..." in preview.variables["style_reference"]
    assert "\n..." in preview.rendered_prompt
