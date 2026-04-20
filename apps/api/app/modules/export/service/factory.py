from __future__ import annotations

from pathlib import Path

from app.shared.runtime.storage_paths import EXPORT_ROOT_DIR

from .export_service import ExportService


def create_export_service(
    *,
    export_root: Path | None = None,
) -> ExportService:
    root = export_root or Path(__file__).resolve().parents[4] / EXPORT_ROOT_DIR
    return ExportService(root)
