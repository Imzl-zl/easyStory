import { requestJson } from "@/lib/api/client";
import type {
  ChapterTaskBatch,
  ChapterTaskDraft,
  ChapterTaskUpdatePayload,
  ChapterTaskView,
  WorkflowExecution,
  WorkflowPausePayload,
  WorkflowStartPayload,
} from "@/lib/api/types";

export function startWorkflow(projectId: string, payload: WorkflowStartPayload = {}) {
  return requestJson<WorkflowExecution>(`/api/v1/projects/${projectId}/workflows/start`, {
    method: "POST",
    body: payload,
  });
}

export function getWorkflow(workflowId: string) {
  return requestJson<WorkflowExecution>(`/api/v1/workflows/${workflowId}`);
}

export function pauseWorkflow(workflowId: string, payload: WorkflowPausePayload = {}) {
  return requestJson<WorkflowExecution>(`/api/v1/workflows/${workflowId}/pause`, {
    method: "POST",
    body: payload,
  });
}

export function resumeWorkflow(workflowId: string) {
  return requestJson<WorkflowExecution>(`/api/v1/workflows/${workflowId}/resume`, {
    method: "POST",
  });
}

export function cancelWorkflow(workflowId: string) {
  return requestJson<WorkflowExecution>(`/api/v1/workflows/${workflowId}/cancel`, {
    method: "POST",
  });
}

export function listChapterTasks(workflowId: string) {
  return requestJson<ChapterTaskView[]>(`/api/v1/workflows/${workflowId}/chapter-tasks`);
}

export function updateChapterTask(
  workflowId: string,
  chapterNumber: number,
  payload: ChapterTaskUpdatePayload,
) {
  return requestJson<ChapterTaskView>(
    `/api/v1/workflows/${workflowId}/chapter-tasks/${chapterNumber}`,
    {
      method: "PUT",
      body: payload,
    },
  );
}

export function regenerateChapterTasks(projectId: string, chapters: ChapterTaskDraft[]) {
  return requestJson<ChapterTaskBatch>(`/api/v1/projects/${projectId}/chapter-tasks/regenerate`, {
    method: "POST",
    body: { chapters },
  });
}
