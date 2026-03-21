import type { WorkflowExecution, WorkflowStatus } from "@/lib/api/types";

export type WorkflowAction = "start" | "pause" | "resume" | "cancel";

export type EngineWorkflowControl = {
  action: WorkflowAction;
  label: string;
  tone: "primary" | "secondary" | "danger";
  disabled?: boolean;
};

export type EngineWorkflowControls = {
  primary: EngineWorkflowControl;
  secondary: EngineWorkflowControl[];
};

const START_CONTROL: EngineWorkflowControl = {
  action: "start",
  label: "启动工作流",
  tone: "primary",
};

const PAUSE_CONTROL: EngineWorkflowControl = {
  action: "pause",
  label: "暂停",
  tone: "primary",
};

const RESUME_CONTROL: EngineWorkflowControl = {
  action: "resume",
  label: "恢复",
  tone: "primary",
};

const CANCEL_CONTROL: EngineWorkflowControl = {
  action: "cancel",
  label: "取消",
  tone: "danger",
};

const CREATED_CONTROL: EngineWorkflowControl = {
  action: "start",
  label: "启动中...",
  tone: "primary",
  disabled: true,
};

const POLLING_STATUSES = new Set<WorkflowStatus>(["created", "running", "paused"]);

export function resolveEngineWorkflowControls(
  workflow: WorkflowExecution | undefined,
): EngineWorkflowControls {
  if (!workflow) {
    return { primary: START_CONTROL, secondary: [] };
  }

  switch (workflow.status) {
    case "created":
      return { primary: CREATED_CONTROL, secondary: [] };
    case "running":
      return { primary: PAUSE_CONTROL, secondary: [CANCEL_CONTROL] };
    case "paused":
    case "failed":
      return { primary: RESUME_CONTROL, secondary: [CANCEL_CONTROL] };
    case "completed":
    case "cancelled":
      return { primary: START_CONTROL, secondary: [] };
  }

  return assertUnreachable(workflow.status);
}

export function shouldPollWorkflow(status: WorkflowStatus | null | undefined): boolean {
  return status ? POLLING_STATUSES.has(status) : false;
}

function assertUnreachable(status: never): never {
  throw new Error(`Unsupported workflow status: ${status}`);
}
