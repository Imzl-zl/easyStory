from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.infrastructure.config_writer import (
    YAML_ROOT_KEY_SKILL,
    clone_config_root,
    write_config_document,
)
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError

from .query_dto import SkillConfigDetailDTO, SkillConfigUpdateDTO
from .query_support import to_skill_detail
from .skill_write_support import (
    build_skill_config,
    ensure_matching_skill_id,
    require_skill,
    serialize_skill_document,
)


class ConfigRegistrySkillWriteService:
    def __init__(self, config_loader: ConfigLoader) -> None:
        self.config_loader = config_loader

    async def update_skill(
        self,
        skill_id: str,
        payload: SkillConfigUpdateDTO,
    ) -> SkillConfigDetailDTO:
        require_skill(self.config_loader, skill_id)
        ensure_matching_skill_id(skill_id, payload.id)
        updated_skill = build_skill_config(payload)
        target_path = self.config_loader.get_source_path(skill_id)
        relative_path = target_path.relative_to(self.config_loader.config_root)
        document = serialize_skill_document(updated_skill)
        self._validate_staged_update(relative_path, document)
        write_config_document(target_path, root_key=YAML_ROOT_KEY_SKILL, payload=document)
        self.config_loader.reload()
        return to_skill_detail(require_skill(self.config_loader, skill_id))

    def _validate_staged_update(
        self,
        relative_path: Path,
        document: dict,
    ) -> None:
        with TemporaryDirectory() as temp_dir:
            staged_root = clone_config_root(self.config_loader.config_root, Path(temp_dir))
            staged_path = staged_root / relative_path
            write_config_document(staged_path, root_key=YAML_ROOT_KEY_SKILL, payload=document)
            try:
                ConfigLoader(staged_root)
            except ConfigurationError as exc:
                raise BusinessRuleError(str(exc)) from exc
