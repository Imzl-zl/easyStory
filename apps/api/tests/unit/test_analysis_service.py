from __future__ import annotations

import pytest

from app.modules.analysis.service import AnalysisCreateDTO, create_analysis_service
from app.shared.runtime.errors import NotFoundError
from tests.unit.models.helpers import create_content, create_project, create_user


def _create_service():
    return create_analysis_service()


def test_analysis_service_creates_lists_and_gets_project_analysis(db) -> None:
    owner = create_user(db)
    project = create_project(db, owner=owner)
    content = create_content(db, project=project, title="样例章节")
    service = _create_service()

    created = service.create_analysis(
        db,
        project.id,
        AnalysisCreateDTO(
            content_id=content.id,
            analysis_type="style",
            source_title="样例小说",
            analysis_scope={"mode": "chapter_range", "chapters": [1, 2, 3]},
            result={"writing_style": {"rhythm": "fast"}},
            suggestions={"keep": ["短句"]},
        ),
        owner_id=owner.id,
    )
    service.create_analysis(
        db,
        project.id,
        AnalysisCreateDTO(
            analysis_type="plot",
            source_title="样例小说",
            analysis_scope={"mode": "sample"},
            result={"structure": "双线叙事"},
        ),
        owner_id=owner.id,
    )

    summaries = service.list_analyses(
        db,
        project.id,
        owner_id=owner.id,
        analysis_type="style",
        content_id=content.id,
    )
    detail = service.get_analysis(db, project.id, created.id, owner_id=owner.id)

    assert created.project_id == project.id
    assert created.content_id == content.id
    assert created.analysis_scope == {"mode": "chapter_range", "chapters": [1, 2, 3]}
    assert len(summaries) == 1
    assert summaries[0].analysis_type == "style"
    assert detail.result["writing_style"]["rhythm"] == "fast"


def test_analysis_service_rejects_foreign_content_reference(db) -> None:
    owner = create_user(db)
    project = create_project(db, owner=owner)
    other_project = create_project(db, owner=owner)
    foreign_content = create_content(db, project=other_project)
    service = _create_service()

    with pytest.raises(NotFoundError):
        service.create_analysis(
            db,
            project.id,
            AnalysisCreateDTO(
                content_id=foreign_content.id,
                analysis_type="style",
                result={"tone": "冷峻"},
            ),
            owner_id=owner.id,
        )


def test_analysis_service_hides_other_users_project(db) -> None:
    owner = create_user(db)
    outsider = create_user(db)
    project = create_project(db, owner=owner)
    service = _create_service()

    with pytest.raises(NotFoundError):
        service.list_analyses(db, project.id, owner_id=outsider.id)
