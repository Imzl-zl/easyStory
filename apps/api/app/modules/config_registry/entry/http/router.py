from __future__ import annotations

from fastapi import APIRouter, Depends

from app.modules.config_registry.service import (
    AgentConfigDetailDTO,
    AgentConfigSummaryDTO,
    AgentConfigUpdateDTO,
    ConfigRegistryAgentWriteService,
    ConfigRegistryQueryService,
    ConfigRegistrySkillWriteService,
    HookConfigSummaryDTO,
    SkillConfigDetailDTO,
    SkillConfigSummaryDTO,
    SkillConfigUpdateDTO,
    WorkflowConfigSummaryDTO,
    create_config_registry_agent_write_service,
    create_config_registry_query_service,
    create_config_registry_skill_write_service,
)
from app.modules.user.entry.http.dependencies import require_config_admin

router = APIRouter(
    prefix="/api/v1/config",
    tags=["config"],
    dependencies=[Depends(require_config_admin)],
)


async def get_config_registry_query_service() -> ConfigRegistryQueryService:
    return create_config_registry_query_service()


async def get_config_registry_agent_write_service() -> ConfigRegistryAgentWriteService:
    return create_config_registry_agent_write_service()


async def get_config_registry_skill_write_service() -> ConfigRegistrySkillWriteService:
    return create_config_registry_skill_write_service()


@router.get("/skills", response_model=list[SkillConfigSummaryDTO])
async def list_skills(
    config_registry_query_service: ConfigRegistryQueryService = Depends(
        get_config_registry_query_service
    ),
) -> list[SkillConfigSummaryDTO]:
    return await config_registry_query_service.list_skills()


@router.get("/skills/{skill_id}", response_model=SkillConfigDetailDTO)
async def get_skill(
    skill_id: str,
    config_registry_query_service: ConfigRegistryQueryService = Depends(
        get_config_registry_query_service
    ),
) -> SkillConfigDetailDTO:
    return await config_registry_query_service.get_skill(skill_id)


@router.put("/skills/{skill_id}", response_model=SkillConfigDetailDTO)
async def update_skill(
    skill_id: str,
    payload: SkillConfigUpdateDTO,
    config_registry_skill_write_service: ConfigRegistrySkillWriteService = Depends(
        get_config_registry_skill_write_service
    ),
) -> SkillConfigDetailDTO:
    return await config_registry_skill_write_service.update_skill(skill_id, payload)


@router.get("/agents", response_model=list[AgentConfigSummaryDTO])
async def list_agents(
    config_registry_query_service: ConfigRegistryQueryService = Depends(
        get_config_registry_query_service
    ),
) -> list[AgentConfigSummaryDTO]:
    return await config_registry_query_service.list_agents()


@router.get("/agents/{agent_id}", response_model=AgentConfigDetailDTO)
async def get_agent(
    agent_id: str,
    config_registry_query_service: ConfigRegistryQueryService = Depends(
        get_config_registry_query_service
    ),
) -> AgentConfigDetailDTO:
    return await config_registry_query_service.get_agent(agent_id)


@router.put("/agents/{agent_id}", response_model=AgentConfigDetailDTO)
async def update_agent(
    agent_id: str,
    payload: AgentConfigUpdateDTO,
    config_registry_agent_write_service: ConfigRegistryAgentWriteService = Depends(
        get_config_registry_agent_write_service
    ),
) -> AgentConfigDetailDTO:
    return await config_registry_agent_write_service.update_agent(agent_id, payload)


@router.get("/hooks", response_model=list[HookConfigSummaryDTO])
async def list_hooks(
    config_registry_query_service: ConfigRegistryQueryService = Depends(
        get_config_registry_query_service
    ),
) -> list[HookConfigSummaryDTO]:
    return await config_registry_query_service.list_hooks()


@router.get("/workflows", response_model=list[WorkflowConfigSummaryDTO])
async def list_workflows(
    config_registry_query_service: ConfigRegistryQueryService = Depends(
        get_config_registry_query_service
    ),
) -> list[WorkflowConfigSummaryDTO]:
    return await config_registry_query_service.list_workflows()
