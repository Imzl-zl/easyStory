import { requestJson } from "@/lib/api/client";
import type { TokenUsageView, WorkflowBillingSummary } from "@/lib/api/types";

export function getWorkflowBillingSummary(workflowId: string) {
  return requestJson<WorkflowBillingSummary>(`/api/v1/workflows/${workflowId}/billing/summary`);
}

export function listWorkflowTokenUsages(workflowId: string) {
  return requestJson<TokenUsageView[]>(`/api/v1/workflows/${workflowId}/billing/token-usages`);
}
