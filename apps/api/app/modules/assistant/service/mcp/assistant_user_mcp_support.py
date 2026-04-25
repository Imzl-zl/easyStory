from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import re
import secrets

import yaml

from app.modules.config_registry.schemas import McpServerConfig
from app.shared.runtime.mcp.mcp_endpoint_policy import normalize_mcp_endpoint_url
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError

from .assistant_mcp_dto import (
    AssistantMcpCreateDTO,
    AssistantMcpDetailDTO,
    AssistantMcpSummaryDTO,
    AssistantMcpUpdateDTO,
    normalize_assistant_mcp_name,
)
from ..preferences.preferences_support import normalize_optional_text

MCP_FILE_NAME = "MCP.yaml"
MCP_SERVERS_DIR_NAME = "mcp_servers"
USER_MCP_ID_PREFIX = "mcp.user."
PROJECT_MCP_ID_PREFIX = "mcp.project."
MCP_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")
SLUG_PATTERN = re.compile(r"[^a-z0-9]+")
YAML_ROOT_KEY_MCP_SERVER = "mcp_server"


@dataclass(frozen=True)
class StoredAssistantMcp:
    id: str
    name: str
    description: str | None
    enabled: bool
    version: str
    transport: str
    url: str
    headers: dict[str, str]
    timeout: int
    updated_at: datetime | None
    path: Path


def build_mcp_summary(record: StoredAssistantMcp) -> AssistantMcpSummaryDTO:
    return AssistantMcpSummaryDTO(
        id=record.id,
        file_name=record.path.name,
        name=record.name,
        description=record.description,
        enabled=record.enabled,
        version=record.version,
        transport=record.transport,
        url=record.url,
        timeout=record.timeout,
        header_count=len(record.headers),
        updated_at=record.updated_at,
    )


def build_mcp_detail(record: StoredAssistantMcp) -> AssistantMcpDetailDTO:
    return AssistantMcpDetailDTO(
        **build_mcp_summary(record).model_dump(),
        headers=dict(record.headers),
    )


def build_runtime_mcp(record: StoredAssistantMcp) -> McpServerConfig:
    return McpServerConfig.model_validate(
        {
            "id": record.id,
            "name": record.name,
            "description": record.description,
            "enabled": record.enabled,
            "version": record.version,
            "transport": record.transport,
            "url": record.url,
            "headers": dict(record.headers),
            "timeout": record.timeout,
        }
    )


def build_user_mcp_path(root: Path, user_id, server_id: str) -> Path:
    validate_mcp_id(server_id)
    return root / "users" / str(user_id) / MCP_SERVERS_DIR_NAME / server_id / MCP_FILE_NAME


def build_project_mcp_path(root: Path, project_id, server_id: str) -> Path:
    validate_mcp_id(server_id)
    return root / "projects" / str(project_id) / MCP_SERVERS_DIR_NAME / server_id / MCP_FILE_NAME


def build_mcp_path(root: Path, user_id, server_id: str) -> Path:
    return build_user_mcp_path(root, user_id, server_id)


def detail_to_record(
    detail: AssistantMcpDetailDTO,
    *,
    path: Path,
    updated_at: datetime | None = None,
) -> StoredAssistantMcp:
    return StoredAssistantMcp(
        id=detail.id,
        name=detail.name,
        description=detail.description,
        enabled=detail.enabled,
        version=detail.version,
        transport=detail.transport,
        url=detail.url,
        headers=dict(detail.headers),
        timeout=detail.timeout,
        updated_at=updated_at,
        path=path,
    )


def create_user_mcp_detail(
    payload: AssistantMcpCreateDTO,
    *,
    reserved_ids: set[str],
    existing_ids: set[str],
) -> AssistantMcpDetailDTO:
    return _create_mcp_detail(
        payload,
        server_id=_resolve_create_mcp_id(
            payload,
            reserved_ids=reserved_ids,
            existing_ids=existing_ids,
            create_id=lambda name, ids: create_user_mcp_id(name, existing_ids=ids),
        ),
    )


def create_project_mcp_detail(
    payload: AssistantMcpCreateDTO,
    *,
    reserved_ids: set[str],
    existing_ids: set[str],
) -> AssistantMcpDetailDTO:
    return _create_mcp_detail(
        payload,
        server_id=_resolve_create_mcp_id(
            payload,
            reserved_ids=reserved_ids,
            existing_ids=existing_ids,
            create_id=lambda name, ids: create_project_mcp_id(name, existing_ids=ids),
        ),
    )


def _create_mcp_detail(
    payload: AssistantMcpCreateDTO,
    *,
    server_id: str,
) -> AssistantMcpDetailDTO:
    return AssistantMcpDetailDTO(
        id=server_id,
        name=payload.name,
        description=normalize_optional_text(payload.description),
        enabled=payload.enabled,
        version=normalize_mcp_version(payload.version),
        transport=normalize_mcp_transport(payload.transport),
        url=normalize_writable_mcp_url(payload.url),
        headers=dict(payload.headers),
        timeout=payload.timeout,
        header_count=len(payload.headers),
        updated_at=None,
    )


def _resolve_create_mcp_id(
    payload: AssistantMcpCreateDTO,
    *,
    reserved_ids: set[str],
    existing_ids: set[str],
    create_id,
) -> str:
    explicit_id = normalize_optional_text(payload.id)
    if explicit_id is not None:
        validate_mcp_id(explicit_id)
        if explicit_id in existing_ids:
            raise BusinessRuleError(f"MCP id 已存在：{explicit_id}")
        return explicit_id
    return create_id(payload.name, reserved_ids | existing_ids)


def update_mcp_detail(
    server_id: str,
    payload: AssistantMcpUpdateDTO,
    *,
    updated_at: datetime | None,
) -> AssistantMcpDetailDTO:
    return AssistantMcpDetailDTO(
        id=server_id,
        name=payload.name,
        description=normalize_optional_text(payload.description),
        enabled=payload.enabled,
        version=normalize_mcp_version(payload.version),
        transport=normalize_mcp_transport(payload.transport),
        url=normalize_writable_mcp_url(payload.url),
        headers=dict(payload.headers),
        timeout=payload.timeout,
        header_count=len(payload.headers),
        updated_at=updated_at,
    )


def format_mcp_document(detail: AssistantMcpDetailDTO) -> str:
    document = build_runtime_mcp(
        detail_to_record(detail, path=Path(MCP_FILE_NAME), updated_at=detail.updated_at)
    ).model_dump(
        exclude_defaults=True,
        exclude_none=True,
    )
    return yaml.safe_dump({YAML_ROOT_KEY_MCP_SERVER: document}, allow_unicode=True, sort_keys=False)


def parse_mcp_document(path: Path, raw_text: str) -> StoredAssistantMcp:
    loaded = yaml.safe_load(raw_text) or {}
    if not isinstance(loaded, dict):
        raise ConfigurationError(f"Assistant MCP file must be a YAML object: {path}")
    document = loaded.get(YAML_ROOT_KEY_MCP_SERVER)
    if not isinstance(document, dict):
        raise ConfigurationError(f"Assistant MCP file is missing mcp_server root: {path}")
    config = McpServerConfig.model_validate(document)
    validate_mcp_id(config.id)
    return StoredAssistantMcp(
        id=config.id,
        name=normalize_assistant_mcp_name(config.name),
        description=normalize_optional_text(config.description),
        enabled=config.enabled,
        version=normalize_mcp_version(config.version),
        transport=normalize_mcp_transport(config.transport),
        url=normalize_mcp_url(config.url),
        headers=dict(config.headers),
        timeout=config.timeout,
        updated_at=datetime.fromtimestamp(path.stat().st_mtime, tz=UTC),
        path=path,
    )


def validate_mcp_id(server_id: str) -> None:
    if not MCP_ID_PATTERN.fullmatch(server_id):
        raise ConfigurationError(f"Assistant MCP id is invalid: {server_id}")


def create_user_mcp_id(name: str, *, existing_ids: set[str]) -> str:
    base_slug = slugify_mcp_name(name)
    while True:
        candidate = f"{USER_MCP_ID_PREFIX}{base_slug}-{secrets.token_hex(3)}"
        if candidate not in existing_ids:
            return candidate


def create_project_mcp_id(name: str, *, existing_ids: set[str]) -> str:
    base_slug = slugify_mcp_name(name)
    while True:
        candidate = f"{PROJECT_MCP_ID_PREFIX}{base_slug}-{secrets.token_hex(3)}"
        if candidate not in existing_ids:
            return candidate


def normalize_mcp_transport(value: str) -> str:
    normalized = value.strip()
    if normalized != "streamable_http":
        raise BusinessRuleError("目前只支持 streamable_http 连接方式。")
    return normalized


def normalize_mcp_url(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise BusinessRuleError("MCP 地址不能为空。")
    return normalized


def normalize_writable_mcp_url(value: str) -> str:
    try:
        return normalize_mcp_endpoint_url(value)
    except ConfigurationError as exc:
        raise BusinessRuleError(str(exc)) from exc


def normalize_mcp_version(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise BusinessRuleError("MCP 版本不能为空。")
    return normalized


def slugify_mcp_name(name: str) -> str:
    normalized = normalize_optional_text(name.lower()) or "mcp-server"
    slug = SLUG_PATTERN.sub("-", normalized).strip("-")
    return slug or "mcp-server"
