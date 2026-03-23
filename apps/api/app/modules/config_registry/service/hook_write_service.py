from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.infrastructure.config_writer import (
    YAML_ROOT_KEY_HOOK,
    clone_config_root,
    write_config_document,
)
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError

from .hook_write_support import (
    build_hook_config,
    ensure_matching_hook_id,
    require_hook,
    serialize_hook_document,
)
from .query_dto import HookConfigDetailDTO, HookConfigUpdateDTO
from .query_support import to_hook_detail


class ConfigRegistryHookWriteService:
    def __init__(self, config_loader: ConfigLoader) -> None:
        self.config_loader = config_loader

    async def update_hook(
        self,
        hook_id: str,
        payload: HookConfigUpdateDTO,
    ) -> HookConfigDetailDTO:
        require_hook(self.config_loader, hook_id)
        ensure_matching_hook_id(hook_id, payload.id)
        updated_hook = build_hook_config(payload)
        target_path = self.config_loader.get_source_path(hook_id)
        relative_path = target_path.relative_to(self.config_loader.config_root)
        document = serialize_hook_document(updated_hook)
        self._validate_staged_update(relative_path, document)
        write_config_document(target_path, root_key=YAML_ROOT_KEY_HOOK, payload=document)
        self.config_loader.reload()
        return to_hook_detail(require_hook(self.config_loader, hook_id))

    def _validate_staged_update(
        self,
        relative_path: Path,
        document: dict,
    ) -> None:
        with TemporaryDirectory() as temp_dir:
            staged_root = clone_config_root(self.config_loader.config_root, Path(temp_dir))
            staged_path = staged_root / relative_path
            write_config_document(staged_path, root_key=YAML_ROOT_KEY_HOOK, payload=document)
            try:
                ConfigLoader(staged_root)
            except ConfigurationError as exc:
                raise BusinessRuleError(str(exc)) from exc
