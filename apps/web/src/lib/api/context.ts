import { requestJson } from "@/lib/api/client";
import type { ContextPreview, ContextPreviewRequest } from "@/lib/api/types";

export function previewWorkflowContext(workflowId: string, payload: ContextPreviewRequest) {
  return requestJson<ContextPreview>(`/api/v1/workflows/${workflowId}/context-preview`, {
    method: "POST",
    body: payload,
  });
}
