import { requestJson } from "@/lib/api/client";
import type { WorkflowReviewAction, WorkflowReviewSummary } from "@/lib/api/types";

export function getWorkflowReviewSummary(workflowId: string) {
  return requestJson<WorkflowReviewSummary>(`/api/v1/workflows/${workflowId}/reviews/summary`);
}

export function listWorkflowReviewActions(workflowId: string) {
  return requestJson<WorkflowReviewAction[]>(`/api/v1/workflows/${workflowId}/reviews/actions`);
}
