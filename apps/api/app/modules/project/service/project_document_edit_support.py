from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectDocumentTextEdit:
    old_text: str
    new_text: str
    context_before: str | None = None
    context_after: str | None = None


@dataclass(frozen=True)
class ResolvedProjectDocumentTextEdit:
    edit_index: int
    start: int
    end: int
    new_text: str


class ProjectDocumentEditApplicationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def apply_project_document_text_edits(
    content: str,
    edits: Iterable[ProjectDocumentTextEdit],
) -> str:
    edit_items = tuple(edits)
    if not edit_items:
        raise ProjectDocumentEditApplicationError(
            "edit_operations_required",
            "至少需要提供一个编辑操作。",
        )
    targets = tuple(
        _resolve_text_edit_target(content, edit, edit_index=index)
        for index, edit in enumerate(edit_items, start=1)
    )
    _raise_if_targets_overlap(targets)
    return _apply_resolved_targets(content, targets)


def _resolve_text_edit_target(
    content: str,
    edit: ProjectDocumentTextEdit,
    *,
    edit_index: int,
) -> ResolvedProjectDocumentTextEdit:
    if edit.old_text == "":
        raise ProjectDocumentEditApplicationError(
            "edit_old_text_required",
            f"第 {edit_index} 个编辑缺少 old_text。",
        )
    candidates = [
        start
        for start in _find_text_occurrences(content, edit.old_text)
        if _matches_edit_context(content, edit, start=start)
    ]
    if not candidates:
        raise ProjectDocumentEditApplicationError(
            "edit_target_not_found",
            f"第 {edit_index} 个编辑没有找到唯一目标片段。",
        )
    if len(candidates) > 1:
        raise ProjectDocumentEditApplicationError(
            "edit_target_ambiguous",
            f"第 {edit_index} 个编辑命中多处，请提供更长 old_text 或上下文锚点。",
        )
    start = candidates[0]
    return ResolvedProjectDocumentTextEdit(
        edit_index=edit_index,
        start=start,
        end=start + len(edit.old_text),
        new_text=edit.new_text,
    )


def _find_text_occurrences(content: str, needle: str) -> tuple[int, ...]:
    matches: list[int] = []
    offset = 0
    while True:
        index = content.find(needle, offset)
        if index < 0:
            return tuple(matches)
        matches.append(index)
        offset = index + 1


def _matches_edit_context(
    content: str,
    edit: ProjectDocumentTextEdit,
    *,
    start: int,
) -> bool:
    end = start + len(edit.old_text)
    if edit.context_before is not None and not content[:start].endswith(edit.context_before):
        return False
    if edit.context_after is not None and not content[end:].startswith(edit.context_after):
        return False
    return True


def _raise_if_targets_overlap(targets: tuple[ResolvedProjectDocumentTextEdit, ...]) -> None:
    ordered = sorted(targets, key=lambda item: (item.start, item.end))
    previous: ResolvedProjectDocumentTextEdit | None = None
    for target in ordered:
        if previous is not None and target.start < previous.end:
            raise ProjectDocumentEditApplicationError(
                "edit_target_overlaps",
                f"第 {previous.edit_index} 个编辑与第 {target.edit_index} 个编辑目标重叠。",
            )
        previous = target


def _apply_resolved_targets(
    content: str,
    targets: tuple[ResolvedProjectDocumentTextEdit, ...],
) -> str:
    parts: list[str] = []
    offset = 0
    for target in sorted(targets, key=lambda item: item.start):
        parts.append(content[offset:target.start])
        parts.append(target.new_text)
        offset = target.end
    parts.append(content[offset:])
    return "".join(parts)
