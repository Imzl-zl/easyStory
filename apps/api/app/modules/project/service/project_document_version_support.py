from __future__ import annotations

import hashlib
import uuid


def build_project_file_document_version(content: str) -> str:
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return f"sha256:{content_hash}"


def build_project_canonical_document_version(
    document_ref: str,
    *,
    content_id: uuid.UUID | None,
    version_number: int | None,
) -> str:
    if content_id is None or version_number is None:
        return f"{document_ref}:empty"
    return f"{document_ref}:version:{content_id}:{version_number}"
