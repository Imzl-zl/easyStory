from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from app.modules.config_registry import ConfigLoader
from app.modules.config_registry.infrastructure.config_writer import (
    YAML_ROOT_KEY_WORKFLOW,
    clone_config_root,
    write_config_document,
)
from app.shared.runtime.errors import BusinessRuleError, ConfigurationError

from .query_dto import WorkflowConfigDetailDTO, WorkflowConfigUpdateDTO
from .workflow_query_support import to_workflow_detail
from .workflow_write_support import (
    build_workflow_config,
    ensure_matching_workflow_id,
    require_workflow,
    serialize_workflow_document,
)


class ConfigRegistryWorkflowWriteService:
    def __init__(self, config_loader: ConfigLoader) -> None:
        self.config_loader = config_loader

    async def update_workflow(
        self,
        workflow_id: str,
        payload: WorkflowConfigUpdateDTO,
    ) -> WorkflowConfigDetailDTO:
        require_workflow(self.config_loader, workflow_id)
        ensure_matching_workflow_id(workflow_id, payload.id)
        updated_workflow = build_workflow_config(payload)
        target_path = self.config_loader.get_source_path(workflow_id)
        relative_path = target_path.relative_to(self.config_loader.config_root)
        document = serialize_workflow_document(updated_workflow)
        self._validate_staged_update(relative_path, document)
        write_config_document(target_path, root_key=YAML_ROOT_KEY_WORKFLOW, payload=document)
        self.config_loader.reload()
        return to_workflow_detail(require_workflow(self.config_loader, workflow_id))

    def _validate_staged_update(
        self,
        relative_path: Path,
        document: dict,
    ) -> None:
        with TemporaryDirectory() as temp_dir:
            staged_root = clone_config_root(self.config_loader.config_root, Path(temp_dir))
            staged_path = staged_root / relative_path
            write_config_document(staged_path, root_key=YAML_ROOT_KEY_WORKFLOW, payload=document)
            try:
                ConfigLoader(staged_root)
            except ConfigurationError as exc:
                raise BusinessRuleError(str(exc)) from exc
