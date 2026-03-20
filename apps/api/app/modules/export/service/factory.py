from __future__ import annotations

from pathlib import Path

from .export_service import EXPORT_ROOT_DIR, ExportService


def create_export_service(
    *,
    export_root: Path | None = None,
) -> ExportService:
    root = export_root or Path(__file__).resolve().parents[4] / EXPORT_ROOT_DIR
    return ExportService(root)
