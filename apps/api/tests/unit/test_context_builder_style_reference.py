from __future__ import annotations

import pytest

from app.modules.analysis.models import Analysis
from app.modules.config_registry.schemas.config_schemas import ContextInjectionItem
from app.modules.context.engine import create_context_builder
from app.modules.context.engine.contracts import STYLE_REFERENCE_MAX_TOKENS
from app.modules.context.engine.errors import ContextBuilderError
from tests.unit.context_builder_test_support import build_context
from tests.unit.models.helpers import create_project


def test_build_context_includes_style_reference_from_analysis(db) -> None:
    builder = create_context_builder()
    project = create_project(db)
    analysis = Analysis(
        project_id=project.id,
        analysis_type="style",
        source_title="样例小说",
        result={
            "writing_style": {"rhythm": "steady"},
            "narrative_perspective": "第三人称限知",
            "tone": "冷峻",
        },
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    variables, report = build_context(
        builder,
        db,
        project.id,
        rules=[
            ContextInjectionItem.model_validate(
                {
                    "type": "style_reference",
                    "analysis_id": str(analysis.id),
                    "inject_fields": ["writing_style", "narrative_perspective"],
                }
            )
        ],
        referenced_variables={"style_reference"},
    )

    assert "style_reference" in variables
    assert "来源标题：样例小说" in variables["style_reference"]
    assert "writing_style" in variables["style_reference"]
    assert "narrative_perspective" in variables["style_reference"]
    assert "tone" not in variables["style_reference"]
    style_reference_report = report["sections"][0]
    assert style_reference_report["type"] == "style_reference"
    assert style_reference_report["status"] == "included"
    assert style_reference_report["selected_fields"] == [
        "writing_style",
        "narrative_perspective",
    ]


def test_build_context_rejects_missing_style_reference_fields(db) -> None:
    builder = create_context_builder()
    project = create_project(db)
    analysis = Analysis(
        project_id=project.id,
        analysis_type="style",
        source_title="样例小说",
        result={"writing_style": {"rhythm": "steady"}},
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    with pytest.raises(ContextBuilderError, match="style_reference fields not found"):
        build_context(
            builder,
            db,
            project.id,
            rules=[
                ContextInjectionItem.model_validate(
                    {
                        "type": "style_reference",
                        "analysis_id": str(analysis.id),
                        "inject_fields": ["writing_style", "tone"],
                    }
                )
            ],
            referenced_variables={"style_reference"},
        )


def test_build_context_rejects_non_style_analysis_for_style_reference(db) -> None:
    builder = create_context_builder()
    project = create_project(db)
    analysis = Analysis(
        project_id=project.id,
        analysis_type="plot",
        source_title="样例小说",
        result={"writing_style": {"rhythm": "steady"}},
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    with pytest.raises(ContextBuilderError, match="style_reference requires style analysis"):
        build_context(
            builder,
            db,
            project.id,
            rules=[
                ContextInjectionItem.model_validate(
                    {
                        "type": "style_reference",
                        "analysis_id": str(analysis.id),
                        "inject_fields": ["writing_style"],
                    }
                )
            ],
            referenced_variables={"style_reference"},
        )


def test_build_context_rejects_missing_analysis_for_style_reference(db) -> None:
    builder = create_context_builder()
    project = create_project(db)

    with pytest.raises(ContextBuilderError, match="style_reference analysis not found"):
        build_context(
            builder,
            db,
            project.id,
            rules=[
                ContextInjectionItem.model_validate(
                    {
                        "type": "style_reference",
                        "analysis_id": "00000000-0000-0000-0000-000000000001",
                        "inject_fields": ["writing_style"],
                    }
                )
            ],
            referenced_variables={"style_reference"},
        )


def test_build_context_truncates_style_reference_to_default_token_cap(db) -> None:
    builder = create_context_builder()
    project = create_project(db)
    analysis = Analysis(
        project_id=project.id,
        analysis_type="style",
        source_title="超长样例小说",
        result={"writing_style": "凌" * 1600},
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    variables, report = build_context(
        builder,
        db,
        project.id,
        rules=[
            ContextInjectionItem.model_validate(
                {
                    "type": "style_reference",
                    "analysis_id": str(analysis.id),
                    "inject_fields": ["writing_style"],
                }
            )
        ],
        referenced_variables={"style_reference"},
    )

    style_reference_report = report["sections"][0]
    assert style_reference_report["status"] == "truncated"
    assert style_reference_report["token_cap"] == STYLE_REFERENCE_MAX_TOKENS
    assert style_reference_report["original_tokens"] > style_reference_report["token_count"]
    assert style_reference_report["token_count"] <= STYLE_REFERENCE_MAX_TOKENS
    assert variables["style_reference"].endswith("\n...")
