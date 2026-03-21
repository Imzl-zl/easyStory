from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from .dto import (
    ContextPreviewDTO,
    ContextPreviewRequestDTO,
    StoryFactConflictStatus,
    StoryFactCreateDTO,
    StoryFactCreateResolution,
    StoryFactDTO,
    StoryFactMutationAction,
    StoryFactMutationResultDTO,
    StoryFactSupersedeDTO,
    StoryFactType,
)

if TYPE_CHECKING:
    from .context_preview_service import ContextPreviewService
    from .story_bible_service import StoryBibleService
    from .factory import create_context_preview_service
    from .story_bible_factory import create_story_bible_service

_LAZY_EXPORTS = {
    "ContextPreviewService": ".context_preview_service",
    "StoryBibleService": ".story_bible_service",
    "create_context_preview_service": ".factory",
    "create_story_bible_service": ".story_bible_factory",
}

__all__ = [
    "ContextPreviewDTO",
    "ContextPreviewRequestDTO",
    "ContextPreviewService",
    "StoryBibleService",
    "StoryFactConflictStatus",
    "StoryFactCreateDTO",
    "StoryFactCreateResolution",
    "StoryFactDTO",
    "StoryFactMutationAction",
    "StoryFactMutationResultDTO",
    "StoryFactSupersedeDTO",
    "StoryFactType",
    "create_context_preview_service",
    "create_story_bible_service",
]


def __getattr__(name: str) -> Any:
    module_name = _LAZY_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name, __name__)
    return getattr(module, name)
