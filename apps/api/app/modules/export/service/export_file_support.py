from __future__ import annotations

import uuid
from pathlib import Path

from app.modules.content.models import Content
from app.modules.export.models import Export
from app.shared.runtime.errors import BusinessRuleError, NotFoundError

EXPORT_FILENAME_PREFIX = "workflow-export"
EXPORT_FILENAME_TOKEN_LENGTH = 8
SUPPORTED_EXPORT_FORMATS = frozenset({"txt", "markdown"})


def resolve_download_path(export_root: Path, export: Export, *, export_id: uuid.UUID) -> Path:
    file_path = (export_root / export.file_path).resolve()
    resolved_root = export_root.resolve()
    if not file_path.is_relative_to(resolved_root):
        raise NotFoundError(f"Export file not found: {export_id}")
    if not file_path.exists() or not file_path.is_file():
        raise NotFoundError(f"Export file not found: {export_id}")
    return file_path


def write_export_file(
    export_root: Path,
    *,
    project_id: uuid.UUID,
    output_dir: Path,
    rendered: list[tuple[Content, str]],
    export_format: str,
    config_snapshot: dict | None,
) -> tuple[Export, Path]:
    if export_format not in SUPPORTED_EXPORT_FORMATS:
        raise BusinessRuleError(f"暂不支持导出格式: {export_format}")
    suffix = "md" if export_format == "markdown" else export_format
    token = uuid.uuid4().hex[:EXPORT_FILENAME_TOKEN_LENGTH]
    filename = f"{EXPORT_FILENAME_PREFIX}-{token}.{suffix}"
    file_path = output_dir / filename
    try:
        file_path.write_text(
            render_document(rendered, markdown=export_format == "markdown"),
            encoding="utf-8",
        )
        return build_export_record(
            export_root,
            file_path,
            project_id=project_id,
            export_format=export_format,
            filename=filename,
            config_snapshot=config_snapshot,
        )
    except Exception:
        if file_path.exists():
            file_path.unlink()
        raise


def build_export_record(
    export_root: Path,
    file_path: Path,
    *,
    project_id: uuid.UUID,
    export_format: str,
    filename: str,
    config_snapshot: dict | None,
) -> tuple[Export, Path]:
    relative_path = file_path.relative_to(export_root).as_posix()
    export = Export(
        project_id=project_id,
        format=export_format,
        filename=filename,
        file_path=relative_path,
        file_size=file_path.stat().st_size,
        config_snapshot=config_snapshot,
    )
    return export, file_path


def cleanup_files(file_paths: list[Path]) -> None:
    for file_path in file_paths:
        if file_path.exists():
            file_path.unlink()


def render_document(
    rendered: list[tuple[Content, str]],
    *,
    markdown: bool,
) -> str:
    lines: list[str] = []
    for chapter, text in rendered:
        title = chapter.title or f"第{chapter.chapter_number}章"
        lines.append(f"# {title}" if markdown else title)
        lines.append("")
        lines.append(text)
        lines.append("")
    return "\n".join(lines).strip() + "\n"
