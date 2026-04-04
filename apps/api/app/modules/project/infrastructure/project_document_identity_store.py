from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import uuid


PROJECT_DOCUMENT_IDENTITY_INDEX_FILE = ".document_identity_index.json"
PROJECT_DOCUMENT_IDENTITY_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ProjectDocumentIdentityRecord:
    document_ref: str
    path: str


class ProjectDocumentIdentityStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def resolve_document_ref(
        self,
        project_id: uuid.UUID,
        *,
        path: str,
    ) -> str:
        state = self._load_state(project_id)
        existing = next((item for item in state["documents"] if item["path"] == path), None)
        if existing is not None:
            return existing["document_ref"]
        document_ref = f"project_file:{uuid.uuid4()}"
        state["documents"].append(
            {
                "document_ref": document_ref,
                "path": path,
            }
        )
        self._write_state(project_id, state)
        return document_ref

    def rename_document_ref(
        self,
        project_id: uuid.UUID,
        *,
        source_path: str,
        target_path: str,
    ) -> None:
        state = self._load_state(project_id)
        updated = False
        for item in state["documents"]:
            current_path = item["path"]
            next_path = _replace_path_prefix(
                current_path,
                source_path=source_path,
                target_path=target_path,
            )
            if next_path is None:
                continue
            item["path"] = next_path
            updated = True
        if not updated:
            return
        self._write_state(project_id, state)

    def delete_document_ref(
        self,
        project_id: uuid.UUID,
        *,
        path: str,
    ) -> None:
        state = self._load_state(project_id)
        next_documents = [
            item
            for item in state["documents"]
            if not _matches_path_prefix(item["path"], path)
        ]
        if len(next_documents) == len(state["documents"]):
            return
        state["documents"] = next_documents
        self._write_state(project_id, state)

    def list_document_identities(
        self,
        project_id: uuid.UUID,
    ) -> tuple[ProjectDocumentIdentityRecord, ...]:
        state = self._load_state(project_id)
        return tuple(
            ProjectDocumentIdentityRecord(
                document_ref=item["document_ref"],
                path=item["path"],
            )
            for item in state["documents"]
        )

    def _load_state(self, project_id: uuid.UUID) -> dict[str, object]:
        index_path = self._resolve_index_path(project_id)
        if not index_path.exists():
            return {
                "schema_version": PROJECT_DOCUMENT_IDENTITY_SCHEMA_VERSION,
                "documents": [],
            }
        payload = json.loads(index_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Project document identity index must be an object")
        documents = payload.get("documents")
        if not isinstance(documents, list):
            raise ValueError("Project document identity index documents must be a list")
        normalized_documents: list[dict[str, str]] = []
        for item in documents:
            if not isinstance(item, dict):
                raise ValueError("Project document identity item must be an object")
            document_ref = item.get("document_ref")
            path = item.get("path")
            if not isinstance(document_ref, str) or not document_ref:
                raise ValueError("Project document identity item document_ref must be a non-empty string")
            if not isinstance(path, str) or not path:
                raise ValueError("Project document identity item path must be a non-empty string")
            normalized_documents.append(
                {
                    "document_ref": document_ref,
                    "path": path,
                }
            )
        return {
            "schema_version": PROJECT_DOCUMENT_IDENTITY_SCHEMA_VERSION,
            "documents": normalized_documents,
        }

    def _write_state(self, project_id: uuid.UUID, state: dict[str, object]) -> None:
        index_path = self._resolve_index_path(project_id)
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _resolve_index_path(self, project_id: uuid.UUID) -> Path:
        return self.root / "projects" / str(project_id) / PROJECT_DOCUMENT_IDENTITY_INDEX_FILE


def _matches_path_prefix(candidate_path: str, prefix_path: str) -> bool:
    return candidate_path == prefix_path or candidate_path.startswith(f"{prefix_path}/")


def _replace_path_prefix(
    candidate_path: str,
    *,
    source_path: str,
    target_path: str,
) -> str | None:
    if candidate_path == source_path:
        return target_path
    prefix = f"{source_path}/"
    if not candidate_path.startswith(prefix):
        return None
    suffix = candidate_path.removeprefix(prefix)
    return f"{target_path}/{suffix}"
