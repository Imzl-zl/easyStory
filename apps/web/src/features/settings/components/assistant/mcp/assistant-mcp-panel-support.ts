import {
  createMyAssistantMcpServer,
  createProjectAssistantMcpServer,
  deleteMyAssistantMcpServer,
  deleteProjectAssistantMcpServer,
  getMyAssistantMcpServer,
  getProjectAssistantMcpServer,
  listMyAssistantMcpServers,
  listProjectAssistantMcpServers,
  updateMyAssistantMcpServer,
  updateProjectAssistantMcpServer,
} from "@/lib/api/assistant-mcp";
import type { AssistantMcpPayload } from "@/lib/api/types";

export type AssistantMcpPanelCopy = {
  createSuccess: string;
  deleteSuccess: string;
  description: string;
  detailLoading: string;
  dirtyMessage: string;
  listLoading: string;
  saveSuccess: string;
  summaryLabel: string;
  title: string;
};

export function buildAssistantMcpListQueryKey(scope: "project" | "user", projectId?: string) {
  return ["assistant-mcp", scope, projectId ?? "me"] as const;
}

export function buildAssistantMcpDetailQueryKey(
  scope: "project" | "user",
  projectId: string | undefined,
  serverId: string | null,
) {
  return ["assistant-mcp", scope, projectId ?? "me", serverId ?? "none"] as const;
}

export function buildAssistantMcpPanelCopy(scope: "project" | "user"): AssistantMcpPanelCopy {
  if (scope === "project") {
    return {
      createSuccess: "项目 MCP 已创建。",
      deleteSuccess: "项目 MCP 已删除。",
      description: "只在当前项目里生效。适合保存这个项目专用的检索入口、资料来源和其他外部工具连接。",
      detailLoading: "正在加载项目 MCP...",
      dirtyMessage: "当前项目 MCP 还有未保存的改动，请先保存或还原。",
      listLoading: "正在读取项目 MCP...",
      saveSuccess: "项目 MCP 已保存。",
      summaryLabel: "项目 MCP",
      title: "项目 MCP",
    };
  }
  return {
    createSuccess: "新的 MCP 已创建。",
    deleteSuccess: "MCP 已删除。",
    description: "你的工具连接配置。把常用外部工具保存下来，通常配合 Hooks 一起使用。",
    detailLoading: "正在加载 MCP...",
    dirtyMessage: "当前 MCP 还有未保存的改动，请先保存或还原。",
    listLoading: "正在读取你的 MCP...",
    saveSuccess: "MCP 已保存。",
    summaryLabel: "我的 MCP",
    title: "MCP",
  };
}

export function loadAssistantMcpServers(scope: "project" | "user", projectId?: string) {
  if (scope === "project") {
    return listProjectAssistantMcpServers(requireProjectId(projectId, "MCP"));
  }
  return listMyAssistantMcpServers();
}

export function loadAssistantMcpDetail(
  scope: "project" | "user",
  projectId: string | undefined,
  serverId: string,
) {
  if (scope === "project") {
    return getProjectAssistantMcpServer(requireProjectId(projectId, "MCP"), serverId);
  }
  return getMyAssistantMcpServer(serverId);
}

export function createAssistantMcp(
  scope: "project" | "user",
  projectId: string | undefined,
  payload: AssistantMcpPayload,
) {
  if (scope === "project") {
    return createProjectAssistantMcpServer(requireProjectId(projectId, "MCP"), payload);
  }
  return createMyAssistantMcpServer(payload);
}

export function updateAssistantMcp(
  scope: "project" | "user",
  projectId: string | undefined,
  serverId: string,
  payload: AssistantMcpPayload,
) {
  if (scope === "project") {
    return updateProjectAssistantMcpServer(requireProjectId(projectId, "MCP"), serverId, payload);
  }
  return updateMyAssistantMcpServer(serverId, payload);
}

export function deleteAssistantMcp(
  scope: "project" | "user",
  projectId: string | undefined,
  serverId: string,
) {
  if (scope === "project") {
    return deleteProjectAssistantMcpServer(requireProjectId(projectId, "MCP"), serverId);
  }
  return deleteMyAssistantMcpServer(serverId);
}

function requireProjectId(projectId: string | undefined, label: string) {
  if (projectId) {
    return projectId;
  }
  throw new Error(`缺少项目 ID，无法读取${label}。`);
}
