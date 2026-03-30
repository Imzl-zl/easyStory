import { requestJson } from "@/lib/api/client";
import type {
  AssistantMcpDetail,
  AssistantMcpPayload,
  AssistantMcpSummary,
} from "@/lib/api/types";

export function listMyAssistantMcpServers() {
  return requestJson<AssistantMcpSummary[]>("/api/v1/assistant/mcp_servers");
}

export function listProjectAssistantMcpServers(projectId: string) {
  return requestJson<AssistantMcpSummary[]>(`/api/v1/assistant/mcp_servers/projects/${projectId}`);
}

export function createMyAssistantMcpServer(payload: AssistantMcpPayload) {
  return requestJson<AssistantMcpDetail>("/api/v1/assistant/mcp_servers", {
    method: "POST",
    body: payload,
  });
}

export function createProjectAssistantMcpServer(
  projectId: string,
  payload: AssistantMcpPayload,
) {
  return requestJson<AssistantMcpDetail>(`/api/v1/assistant/mcp_servers/projects/${projectId}`, {
    method: "POST",
    body: payload,
  });
}

export function getMyAssistantMcpServer(serverId: string) {
  return requestJson<AssistantMcpDetail>(`/api/v1/assistant/mcp_servers/${serverId}`);
}

export function getProjectAssistantMcpServer(projectId: string, serverId: string) {
  return requestJson<AssistantMcpDetail>(
    `/api/v1/assistant/mcp_servers/projects/${projectId}/${serverId}`,
  );
}

export function updateMyAssistantMcpServer(serverId: string, payload: AssistantMcpPayload) {
  return requestJson<AssistantMcpDetail>(`/api/v1/assistant/mcp_servers/${serverId}`, {
    method: "PUT",
    body: payload,
  });
}

export function updateProjectAssistantMcpServer(
  projectId: string,
  serverId: string,
  payload: AssistantMcpPayload,
) {
  return requestJson<AssistantMcpDetail>(
    `/api/v1/assistant/mcp_servers/projects/${projectId}/${serverId}`,
    {
      method: "PUT",
      body: payload,
    },
  );
}

export function deleteMyAssistantMcpServer(serverId: string) {
  return requestJson<void>(`/api/v1/assistant/mcp_servers/${serverId}`, {
    method: "DELETE",
  });
}

export function deleteProjectAssistantMcpServer(projectId: string, serverId: string) {
  return requestJson<void>(`/api/v1/assistant/mcp_servers/projects/${projectId}/${serverId}`, {
    method: "DELETE",
  });
}
