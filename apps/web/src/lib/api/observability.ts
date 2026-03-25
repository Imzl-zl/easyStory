import { requestJson } from "@/lib/api/client";
import type {
  AuditLogView,
  ExecutionLogView,
  NodeExecutionView,
  PromptReplayView,
} from "@/lib/api/types";

export function listProjectAuditLogs(projectId: string, eventType?: string, limit = 100) {
  const search = new URLSearchParams({ limit: String(limit) });
  if (eventType) {
    search.set("event_type", eventType);
  }
  return requestJson<AuditLogView[]>(`/api/v1/projects/${projectId}/audit-logs?${search.toString()}`);
}

export function listCredentialAuditLogs(credentialId: string, eventType?: string, limit = 100) {
  const search = new URLSearchParams({ limit: String(limit) });
  if (eventType) {
    search.set("event_type", eventType);
  }
  return requestJson<AuditLogView[]>(
    `/api/v1/credentials/${credentialId}/audit-logs?${search.toString()}`,
  );
}

export function listWorkflowExecutions(workflowId: string) {
  return requestJson<NodeExecutionView[]>(`/api/v1/workflows/${workflowId}/executions`);
}

export function listWorkflowLogs(workflowId: string) {
  return requestJson<ExecutionLogView[]>(`/api/v1/workflows/${workflowId}/logs`);
}

export function listPromptReplays(workflowId: string, nodeExecutionId: string) {
  return requestJson<PromptReplayView[]>(
    `/api/v1/workflows/${workflowId}/node-executions/${nodeExecutionId}/prompt-replays`,
  );
}
