"""Workflow application services."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from .chapter_task_dto import (
    ChapterTaskBatchDTO,
    ChapterTaskDraftDTO,
    ChapterTaskRegenerateDTO,
    ChapterTaskUpdateDTO,
    ChapterTaskViewDTO,
)
from .dto import WorkflowExecutionDTO, WorkflowPauseDTO, WorkflowStartDTO

if TYPE_CHECKING:
    from .chapter_task_service import ChapterTaskService
    from .workflow_app_service import WorkflowAppService
    from .workflow_runtime_service import WorkflowRuntimeService
    from .workflow_service import WorkflowService
    from .factory import (
        create_chapter_task_service,
        create_workflow_app_service,
        create_workflow_runtime_service,
        create_workflow_service,
    )

_LAZY_EXPORTS = {
    "ChapterTaskService": ".chapter_task_service",
    "WorkflowAppService": ".workflow_app_service",
    "WorkflowRuntimeService": ".workflow_runtime_service",
    "WorkflowService": ".workflow_service",
    "create_chapter_task_service": ".factory",
    "create_workflow_app_service": ".factory",
    "create_workflow_runtime_service": ".factory",
    "create_workflow_service": ".factory",
}

__all__ = [
    "ChapterTaskBatchDTO",
    "ChapterTaskDraftDTO",
    "ChapterTaskRegenerateDTO",
    "ChapterTaskService",
    "ChapterTaskUpdateDTO",
    "ChapterTaskViewDTO",
    "WorkflowAppService",
    "WorkflowExecutionDTO",
    "WorkflowPauseDTO",
    "WorkflowRuntimeService",
    "WorkflowService",
    "WorkflowStartDTO",
    "create_chapter_task_service",
    "create_workflow_app_service",
    "create_workflow_runtime_service",
    "create_workflow_service",
]


def __getattr__(name: str) -> Any:
    module_name = _LAZY_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name, __name__)
    return getattr(module, name)
