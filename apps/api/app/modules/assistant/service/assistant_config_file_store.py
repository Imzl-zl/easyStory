from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import uuid

import yaml

from app.shared.runtime.errors import ConfigurationError

from .assistant_rule_dto import AssistantRuleProfileDTO, AssistantRuleProfileUpdateDTO
from .assistant_rule_support import normalize_rule_content
from .preferences_dto import AssistantPreferencesDTO, AssistantPreferencesUpdateDTO
from .preferences_support import build_preferences_dto, build_updated_preferences

RULE_FILE_NAME = "AGENTS.md"
PREFERENCES_FILE_NAME = "preferences.yaml"
PROJECT_DIR_NAME = "projects"
USER_DIR_NAME = "users"
FRONTMATTER_BOUNDARY = "---"


@dataclass(frozen=True)
class RuleFileRecord:
    enabled: bool
    content: str
    updated_at: datetime | None


class AssistantConfigFileStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def load_user_rule(self, user_id: uuid.UUID) -> AssistantRuleProfileDTO:
        return self._load_rule("user", self._user_rule_path(user_id))

    def save_user_rule(
        self,
        user_id: uuid.UUID,
        payload: AssistantRuleProfileUpdateDTO,
    ) -> AssistantRuleProfileDTO:
        return self._save_rule("user", self._user_rule_path(user_id), payload)

    def load_project_rule(self, project_id: uuid.UUID) -> AssistantRuleProfileDTO:
        return self._load_rule("project", self._project_rule_path(project_id))

    def save_project_rule(
        self,
        project_id: uuid.UUID,
        payload: AssistantRuleProfileUpdateDTO,
    ) -> AssistantRuleProfileDTO:
        return self._save_rule("project", self._project_rule_path(project_id), payload)

    def load_preferences(self, user_id: uuid.UUID) -> AssistantPreferencesDTO:
        return _read_preferences_file(self._user_preferences_path(user_id))

    def save_preferences(
        self,
        user_id: uuid.UUID,
        payload: AssistantPreferencesUpdateDTO,
    ) -> AssistantPreferencesDTO:
        path = self._user_preferences_path(user_id)
        preferences = build_updated_preferences(payload)
        if preferences.default_provider is None and preferences.default_model_name is None:
            _delete_if_exists(path)
            return AssistantPreferencesDTO()
        _write_preferences_file(path, preferences)
        return _read_preferences_file(path)

    def _load_rule(
        self,
        scope: str,
        path: Path,
    ) -> AssistantRuleProfileDTO:
        record = _read_rule_file(path, expected_scope=scope)
        if record is None:
            return AssistantRuleProfileDTO(scope=scope, enabled=False, content="", updated_at=None)
        return AssistantRuleProfileDTO(
            scope=scope,
            enabled=record.enabled,
            content=record.content,
            updated_at=record.updated_at,
        )

    def _save_rule(
        self,
        scope: str,
        path: Path,
        payload: AssistantRuleProfileUpdateDTO,
    ) -> AssistantRuleProfileDTO:
        content = normalize_rule_content(payload.content)
        if not payload.enabled and not content:
            _delete_if_exists(path)
            return AssistantRuleProfileDTO(scope=scope, enabled=False, content="", updated_at=None)
        _write_rule_file(path, enabled=payload.enabled, scope=scope, content=content)
        return self._load_rule(scope, path)

    def _user_dir(self, user_id: uuid.UUID) -> Path:
        return self.root / USER_DIR_NAME / str(user_id)

    def _project_dir(self, project_id: uuid.UUID) -> Path:
        return self.root / PROJECT_DIR_NAME / str(project_id)

    def _user_rule_path(self, user_id: uuid.UUID) -> Path:
        return self._user_dir(user_id) / RULE_FILE_NAME

    def _project_rule_path(self, project_id: uuid.UUID) -> Path:
        return self._project_dir(project_id) / RULE_FILE_NAME

    def _user_preferences_path(self, user_id: uuid.UUID) -> Path:
        return self._user_dir(user_id) / PREFERENCES_FILE_NAME


def _read_rule_file(path: Path, *, expected_scope: str) -> RuleFileRecord | None:
    if not path.exists():
        return None
    raw_text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    enabled, scope, content = _parse_rule_frontmatter(raw_text)
    if scope is not None and scope != expected_scope:
        raise ConfigurationError(
            f"Assistant rule file scope mismatch at {path}: expected {expected_scope}, got {scope}"
        )
    return RuleFileRecord(
        enabled=enabled,
        content=normalize_rule_content(content),
        updated_at=_resolve_file_updated_at(path),
    )


def _parse_rule_frontmatter(raw_text: str) -> tuple[bool, str | None, str]:
    if not raw_text.startswith(f"{FRONTMATTER_BOUNDARY}\n"):
        return True, None, raw_text
    parts = raw_text.split(f"\n{FRONTMATTER_BOUNDARY}\n", maxsplit=1)
    if len(parts) != 2:
        raise ConfigurationError("Assistant rule file frontmatter is not properly closed")
    metadata_text = parts[0].removeprefix(f"{FRONTMATTER_BOUNDARY}\n")
    metadata = yaml.safe_load(metadata_text) or {}
    if not isinstance(metadata, dict):
        raise ConfigurationError("Assistant rule file frontmatter must be a YAML object")
    enabled = bool(metadata.get("enabled", True))
    scope = metadata.get("scope")
    if scope is not None and not isinstance(scope, str):
        raise ConfigurationError("Assistant rule file scope must be a string")
    return enabled, scope, parts[1]


def _write_rule_file(path: Path, *, enabled: bool, scope: str, content: str) -> None:
    metadata = yaml.safe_dump(
        {"enabled": enabled, "scope": scope},
        allow_unicode=True,
        sort_keys=False,
    ).strip()
    body = f"{FRONTMATTER_BOUNDARY}\n{metadata}\n{FRONTMATTER_BOUNDARY}\n\n{content}\n"
    _ensure_parent_dir(path)
    path.write_text(body, encoding="utf-8")


def _read_preferences_file(path: Path) -> AssistantPreferencesDTO:
    if not path.exists():
        return AssistantPreferencesDTO()
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ConfigurationError(f"Assistant preferences file must be a YAML object: {path}")
    return build_preferences_dto(
        default_provider=raw.get("default_provider"),
        default_model_name=raw.get("default_model_name"),
    )


def _write_preferences_file(path: Path, preferences: AssistantPreferencesDTO) -> None:
    payload = {
        "default_provider": preferences.default_provider,
        "default_model_name": preferences.default_model_name,
    }
    _ensure_parent_dir(path)
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _delete_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()


def _resolve_file_updated_at(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
