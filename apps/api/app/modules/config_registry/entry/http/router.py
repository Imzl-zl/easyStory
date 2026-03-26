from __future__ import annotations

from fastapi import APIRouter, Depends

from app.modules.config_registry.service import (
    AgentConfigDetailDTO,
    AgentConfigSummaryDTO,
    AgentConfigUpdateDTO,
    ConfigRegistryAgentWriteService,
    ConfigRegistryHookWriteService,
    ConfigRegistryMcpWriteService,
    ConfigRegistryQueryService,
    ConfigRegistrySkillWriteService,
    ConfigRegistryWorkflowWriteService,
    HookConfigDetailDTO,
    HookConfigSummaryDTO,
    HookConfigUpdateDTO,
    McpServerConfigDetailDTO,
    McpServerConfigSummaryDTO,
    McpServerConfigUpdateDTO,
    SkillConfigDetailDTO,
    SkillConfigSummaryDTO,
    SkillConfigUpdateDTO,
    WorkflowConfigDetailDTO,
    WorkflowConfigSummaryDTO,
    WorkflowConfigUpdateDTO,
    create_config_registry_agent_write_service,
    create_config_registry_hook_write_service,
    create_config_registry_mcp_write_service,
    create_config_registry_query_service,
    create_config_registry_skill_write_service,
    create_config_registry_workflow_write_service,
)
from app.modules.user.entry.http.dependencies import require_control_plane_admin

router = APIRouter(
    prefix="/api/v1/config",
    tags=["config"],
    dependencies=[Depends(require_control_plane_admin)],
)


async def get_config_registry_query_service() -> ConfigRegistryQueryService:
    return create_config_registry_query_service()


async def get_config_registry_agent_write_service() -> ConfigRegistryAgentWriteService:
    return create_config_registry_agent_write_service()


async def get_config_registry_hook_write_service() -> ConfigRegistryHookWriteService:
    return create_config_registry_hook_write_service()


async def get_config_registry_mcp_write_service() -> ConfigRegistryMcpWriteService:
    return create_config_registry_mcp_write_service()


async def get_config_registry_skill_write_service() -> ConfigRegistrySkillWriteService:
    return create_config_registry_skill_write_service()


async def get_config_registry_workflow_write_service() -> ConfigRegistryWorkflowWriteService:
    return create_config_registry_workflow_write_service()


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


@router.get("/hooks/{hook_id}", response_model=HookConfigDetailDTO)
async def get_hook(
    hook_id: str,
    config_registry_query_service: ConfigRegistryQueryService = Depends(
        get_config_registry_query_service
    ),
) -> HookConfigDetailDTO:
    return await config_registry_query_service.get_hook(hook_id)


@router.put("/hooks/{hook_id}", response_model=HookConfigDetailDTO)
async def update_hook(
    hook_id: str,
    payload: HookConfigUpdateDTO,
    config_registry_hook_write_service: ConfigRegistryHookWriteService = Depends(
        get_config_registry_hook_write_service
    ),
) -> HookConfigDetailDTO:
    return await config_registry_hook_write_service.update_hook(hook_id, payload)


@router.get("/mcp_servers", response_model=list[McpServerConfigSummaryDTO])
async def list_mcp_servers(
    config_registry_query_service: ConfigRegistryQueryService = Depends(
        get_config_registry_query_service
    ),
) -> list[McpServerConfigSummaryDTO]:
    return await config_registry_query_service.list_mcp_servers()


@router.get("/mcp_servers/{server_id}", response_model=McpServerConfigDetailDTO)
async def get_mcp_server(
    server_id: str,
    config_registry_query_service: ConfigRegistryQueryService = Depends(
        get_config_registry_query_service
    ),
) -> McpServerConfigDetailDTO:
    return await config_registry_query_service.get_mcp_server(server_id)


@router.put("/mcp_servers/{server_id}", response_model=McpServerConfigDetailDTO)
async def update_mcp_server(
    server_id: str,
    payload: McpServerConfigUpdateDTO,
    config_registry_mcp_write_service: ConfigRegistryMcpWriteService = Depends(
        get_config_registry_mcp_write_service
    ),
) -> McpServerConfigDetailDTO:
    return await config_registry_mcp_write_service.update_mcp_server(server_id, payload)


@router.get("/workflows", response_model=list[WorkflowConfigSummaryDTO])
async def list_workflows(
    config_registry_query_service: ConfigRegistryQueryService = Depends(
        get_config_registry_query_service
    ),
) -> list[WorkflowConfigSummaryDTO]:
    return await config_registry_query_service.list_workflows()


@router.get("/workflows/{workflow_id}", response_model=WorkflowConfigDetailDTO)
async def get_workflow(
    workflow_id: str,
    config_registry_query_service: ConfigRegistryQueryService = Depends(
        get_config_registry_query_service
    ),
) -> WorkflowConfigDetailDTO:
    return await config_registry_query_service.get_workflow(workflow_id)


@router.put("/workflows/{workflow_id}", response_model=WorkflowConfigDetailDTO)
async def update_workflow(
    workflow_id: str,
    payload: WorkflowConfigUpdateDTO,
    config_registry_workflow_write_service: ConfigRegistryWorkflowWriteService = Depends(
        get_config_registry_workflow_write_service
    ),
) -> WorkflowConfigDetailDTO:
    return await config_registry_workflow_write_service.update_workflow(workflow_id, payload)
