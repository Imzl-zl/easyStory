import { requestJson } from "@/lib/api/client";
import type { ExecutionLogView, NodeExecutionView, PromptReplayView } from "@/lib/api/types";

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
