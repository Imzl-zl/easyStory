import type { ProjectPreparationStatus } from "@/lib/api/types";

export function resolvePreparationWorkflowId(
  preparation: ProjectPreparationStatus | undefined,
): string | null {
  return (
    preparation?.chapter_tasks.workflow_execution_id ??
    preparation?.active_workflow?.execution_id ??
    null
  );
}

export function buildEngineTaskHref(projectId: string, workflowId: string | null): string {
  const basePath = `/workspace/project/${projectId}/engine`;
  return workflowId ? `${basePath}?tab=tasks&workflow=${workflowId}` : basePath;
}

export function getEngineTaskCtaLabel(workflowId: string | null): string {
  return workflowId ? "前往 Engine 任务面板" : "前往 Engine 载入 workflow";
}
