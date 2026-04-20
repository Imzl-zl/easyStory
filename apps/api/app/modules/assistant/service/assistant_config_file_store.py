from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import uuid

import yaml

from app.shared.runtime.errors import ConfigurationError

from .rules.assistant_rule_dto import AssistantRuleProfileDTO, AssistantRuleProfileUpdateDTO
from .rules.assistant_rule_support import (
    assemble_rule_runtime_content,
    normalize_rule_content,
    normalize_rule_include_paths,
)
from .preferences.preferences_dto import (
    AssistantPreferencesDTO,
    AssistantPreferencesUpdateDTO,
)
from .preferences.preferences_support import (
    build_preferences_dto,
    build_updated_preferences,
    has_custom_preferences,
    merge_preferences,
)

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
    include_paths: tuple[str, ...] = ()


class AssistantConfigFileStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def load_user_rule(self, user_id: uuid.UUID) -> AssistantRuleProfileDTO:
        return self._load_rule("user", self._user_rule_path(user_id))

    def resolve_user_rule_runtime_content(self, user_id: uuid.UUID) -> str | None:
        return _resolve_rule_runtime_content(self._user_rule_path(user_id), expected_scope="user")

    def save_user_rule(
        self,
        user_id: uuid.UUID,
        payload: AssistantRuleProfileUpdateDTO,
    ) -> AssistantRuleProfileDTO:
        return self._save_rule("user", self._user_rule_path(user_id), payload)

    def load_project_rule(self, project_id: uuid.UUID) -> AssistantRuleProfileDTO:
        return self._load_rule("project", self._project_rule_path(project_id))

    def resolve_project_rule_runtime_content(self, project_id: uuid.UUID) -> str | None:
        return _resolve_rule_runtime_content(
            self._project_rule_path(project_id),
            expected_scope="project",
        )

    def save_project_rule(
        self,
        project_id: uuid.UUID,
        payload: AssistantRuleProfileUpdateDTO,
    ) -> AssistantRuleProfileDTO:
        return self._save_rule("project", self._project_rule_path(project_id), payload)

    def load_user_preferences(self, user_id: uuid.UUID) -> AssistantPreferencesDTO:
        return _read_preferences_file(self._user_preferences_path(user_id))

    def save_user_preferences(
        self,
        user_id: uuid.UUID,
        payload: AssistantPreferencesUpdateDTO,
    ) -> AssistantPreferencesDTO:
        return self._save_preferences(self._user_preferences_path(user_id), payload)

    def load_project_preferences(self, project_id: uuid.UUID) -> AssistantPreferencesDTO:
        return _read_preferences_file(self._project_preferences_path(project_id))

    def save_project_preferences(
        self,
        project_id: uuid.UUID,
        payload: AssistantPreferencesUpdateDTO,
    ) -> AssistantPreferencesDTO:
        return self._save_preferences(self._project_preferences_path(project_id), payload)

    def resolve_preferences(
        self,
        *,
        user_id: uuid.UUID,
        project_id: uuid.UUID | None,
    ) -> AssistantPreferencesDTO:
        user_preferences = self.load_user_preferences(user_id)
        if project_id is None:
            return user_preferences
        return merge_preferences(user_preferences, self.load_project_preferences(project_id))

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
        existing_record = _read_rule_file(path, expected_scope=scope)
        include_paths = existing_record.include_paths if existing_record is not None else ()
        if not payload.enabled and not content and not include_paths:
            _delete_if_exists(path)
            return AssistantRuleProfileDTO(scope=scope, enabled=False, content="", updated_at=None)
        _write_rule_file(
            path,
            enabled=payload.enabled,
            scope=scope,
            content=content,
            include_paths=include_paths,
        )
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

    def _project_preferences_path(self, project_id: uuid.UUID) -> Path:
        return self._project_dir(project_id) / PREFERENCES_FILE_NAME

    def _save_preferences(
        self,
        path: Path,
        payload: AssistantPreferencesUpdateDTO,
    ) -> AssistantPreferencesDTO:
        preferences = build_updated_preferences(payload)
        if not has_custom_preferences(preferences):
            _delete_if_exists(path)
            return build_preferences_dto()
        _write_preferences_file(path, preferences)
        return _read_preferences_file(path)


def _read_rule_file(path: Path, *, expected_scope: str) -> RuleFileRecord | None:
    if not path.exists():
        return None
    raw_text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    enabled, scope, include_paths, content = _parse_rule_frontmatter(raw_text)
    if scope is not None and scope != expected_scope:
        raise ConfigurationError(
            f"Assistant rule file scope mismatch at {path}: expected {expected_scope}, got {scope}"
        )
    return RuleFileRecord(
        enabled=enabled,
        content=normalize_rule_content(content),
        updated_at=_resolve_file_updated_at(path),
        include_paths=include_paths,
    )


def _parse_rule_frontmatter(raw_text: str) -> tuple[bool, str | None, tuple[str, ...], str]:
    if not raw_text.startswith(f"{FRONTMATTER_BOUNDARY}\n"):
        return True, None, (), raw_text
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
    include_paths = normalize_rule_include_paths(metadata.get("include"))
    return enabled, scope, include_paths, parts[1]


def _write_rule_file(
    path: Path,
    *,
    enabled: bool,
    scope: str,
    content: str,
    include_paths: tuple[str, ...] = (),
) -> None:
    metadata: dict[str, object] = {"enabled": enabled, "scope": scope}
    if include_paths:
        metadata["include"] = list(include_paths)
    metadata = yaml.safe_dump(
        metadata,
        allow_unicode=True,
        sort_keys=False,
    ).strip()
    body = f"{FRONTMATTER_BOUNDARY}\n{metadata}\n{FRONTMATTER_BOUNDARY}\n\n{content}\n"
    _ensure_parent_dir(path)
    path.write_text(body, encoding="utf-8")


def _resolve_rule_runtime_content(path: Path, *, expected_scope: str) -> str | None:
    record = _read_rule_file(path, expected_scope=expected_scope)
    if record is None or not record.enabled:
        return None
    sections = _collect_rule_runtime_sections(
        path,
        expected_scope=expected_scope,
        scope_root=path.parent.resolve(),
        stack=(),
    )
    return assemble_rule_runtime_content(*sections) or None


def _collect_rule_runtime_sections(
    path: Path,
    *,
    expected_scope: str,
    scope_root: Path,
    stack: tuple[Path, ...],
) -> tuple[str, ...]:
    resolved_path = path.resolve()
    if resolved_path in stack:
        cycle_paths = stack + (resolved_path,)
        cycle = " -> ".join(_format_rule_relative_path(item, scope_root) for item in cycle_paths)
        raise ConfigurationError(f"Assistant rule include cycle detected: {cycle}")
    record = _read_rule_file(resolved_path, expected_scope=expected_scope)
    if record is None:
        missing_path = _format_rule_relative_path(resolved_path, scope_root)
        raise ConfigurationError(f"Assistant rule include target does not exist: {missing_path}")
    if not record.enabled:
        return ()
    sections: list[str] = []
    if record.content:
        sections.append(record.content)
    next_stack = stack + (resolved_path,)
    for include_path in record.include_paths:
        included_path = _resolve_included_rule_path(
            base_path=resolved_path,
            include_path=include_path,
            scope_root=scope_root,
            expected_scope=expected_scope,
        )
        sections.extend(
            _collect_rule_runtime_sections(
                included_path,
                expected_scope=expected_scope,
                scope_root=scope_root,
                stack=next_stack,
            )
        )
    return tuple(sections)


def _resolve_included_rule_path(
    *,
    base_path: Path,
    include_path: str,
    scope_root: Path,
    expected_scope: str,
) -> Path:
    include_reference = Path(include_path)
    if include_reference.is_absolute():
        raise ConfigurationError(
            f"Assistant rule include must be relative within {expected_scope} scope: {include_path}"
        )
    resolved_path = (base_path.parent / include_reference).resolve()
    if not resolved_path.is_relative_to(scope_root):
        raise ConfigurationError(
            f"Assistant rule include must stay within {expected_scope} scope root: {include_path}"
        )
    if not resolved_path.exists() or not resolved_path.is_file():
        missing_path = _format_rule_relative_path(resolved_path, scope_root)
        raise ConfigurationError(f"Assistant rule include target does not exist: {missing_path}")
    return resolved_path


def _format_rule_relative_path(path: Path, scope_root: Path) -> str:
    try:
        return path.relative_to(scope_root).as_posix()
    except ValueError:
        return str(path)


def _read_preferences_file(path: Path) -> AssistantPreferencesDTO:
    if not path.exists():
        return build_preferences_dto()
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ConfigurationError(f"Assistant preferences file must be a YAML object: {path}")
    return build_preferences_dto(
        default_provider=raw.get("default_provider"),
        default_model_name=raw.get("default_model_name"),
        default_max_output_tokens=raw.get("default_max_output_tokens"),
        default_reasoning_effort=raw.get("default_reasoning_effort"),
        default_thinking_level=raw.get("default_thinking_level"),
        default_thinking_budget=raw.get("default_thinking_budget"),
    )


def _write_preferences_file(path: Path, preferences: AssistantPreferencesDTO) -> None:
    payload: dict[str, str | int] = {}
    if preferences.default_provider is not None:
        payload["default_provider"] = preferences.default_provider
    if preferences.default_model_name is not None:
        payload["default_model_name"] = preferences.default_model_name
    if preferences.default_max_output_tokens is not None:
        payload["default_max_output_tokens"] = preferences.default_max_output_tokens
    if preferences.default_reasoning_effort is not None:
        payload["default_reasoning_effort"] = preferences.default_reasoning_effort
    if preferences.default_thinking_level is not None:
        payload["default_thinking_level"] = preferences.default_thinking_level
    if preferences.default_thinking_budget is not None:
        payload["default_thinking_budget"] = preferences.default_thinking_budget
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
