"use client";

import { useEffect } from "react";

import type { NodeExecutionView, ProjectPreparationStatus } from "@/lib/api/types";

export type WorkflowBoundValue<T> = {
  value: T;
  workflowId: string;
};

export function buildEnginePathWithParams(
  pathname: string,
  currentSearch: string,
  patches: Record<string, string | null>,
): string {
  const next = new URLSearchParams(currentSearch);
  Object.entries(patches).forEach(([key, value]) => {
    if (value === null) {
      next.delete(key);
      return;
    }
    next.set(key, value);
  });
  const search = next.toString();
  return search ? `${pathname}?${search}` : pathname;
}

export function createWorkflowBoundValue<T>(
  workflowId: string,
  value: T,
): WorkflowBoundValue<T> {
  return { value, workflowId };
}

export function resolveWorkflowBoundValue<T>(
  state: WorkflowBoundValue<T>,
  workflowId: string,
  fallbackValue: T,
): T {
  return state.workflowId === workflowId ? state.value : fallbackValue;
}

export function shouldRememberWorkflow({
  hasWorkflow,
  rememberedWorkflowId,
  workflowId,
}: {
  hasWorkflow: boolean;
  rememberedWorkflowId: string | undefined;
  workflowId: string;
}): boolean {
  return hasWorkflow && workflowId.length > 0 && rememberedWorkflowId !== workflowId;
}

export function shouldResetSelectedExecution({
  executions,
  selectedExecutionId,
}: {
  executions: NodeExecutionView[];
  selectedExecutionId: string;
}): boolean {
  if (!selectedExecutionId) {
    return false;
  }
  return !executions.some((execution) => execution.id === selectedExecutionId);
}

export function resolveReplayExecutionSelection({
  canValidateSelection,
  executions,
  selectedExecutionId,
}: {
  canValidateSelection: boolean;
  executions: NodeExecutionView[];
  selectedExecutionId: string;
}): {
  activeSelectedExecutionId: string;
  shouldClearExecutionParam: boolean;
} {
  if (!selectedExecutionId) {
    return {
      activeSelectedExecutionId: "",
      shouldClearExecutionParam: false,
    };
  }
  if (!canValidateSelection) {
    return {
      activeSelectedExecutionId: "",
      shouldClearExecutionParam: false,
    };
  }
  if (shouldResetSelectedExecution({ executions, selectedExecutionId })) {
    return {
      activeSelectedExecutionId: "",
      shouldClearExecutionParam: true,
    };
  }
  return {
    activeSelectedExecutionId: selectedExecutionId,
    shouldClearExecutionParam: false,
  };
}

export function resolveExecutionParamForWorkflow({
  currentExecutionId,
  currentWorkflowId,
  nextWorkflowId,
}: {
  currentExecutionId: string;
  currentWorkflowId: string;
  nextWorkflowId: string;
}): string | null {
  if (!currentExecutionId) {
    return null;
  }
  if (!currentWorkflowId) {
    return null;
  }
  return currentWorkflowId === nextWorkflowId ? currentExecutionId : null;
}

export function resolveStartWorkflowDisabledReason({
  action,
  errorMessage,
  isLoading,
  preparation,
}: {
  action: "start" | "pause" | "resume" | "cancel";
  errorMessage: string | null;
  isLoading: boolean;
  preparation: ProjectPreparationStatus | undefined;
}): string | null {
  if (action !== "start") {
    return null;
  }
  if (isLoading) {
    return "正在检查项目设定与前置资产状态。";
  }
  if (errorMessage) {
    return errorMessage;
  }
  if (!preparation) {
    return "当前无法确认项目前置状态，暂不可启动工作流。";
  }
  if (!preparation.can_start_workflow) {
    return preparation.next_step_detail;
  }
  return null;
}

export function useRememberLastWorkflow({
  hasWorkflow,
  projectId,
  rememberedWorkflowId,
  setLastWorkflow,
  workflowId,
}: {
  hasWorkflow: boolean;
  projectId: string;
  rememberedWorkflowId: string | undefined;
  setLastWorkflow: (projectId: string, workflowId: string) => void;
  workflowId: string;
}): void {
  useEffect(() => {
    if (!shouldRememberWorkflow({ hasWorkflow, rememberedWorkflowId, workflowId })) {
      return;
    }
    setLastWorkflow(projectId, workflowId);
  }, [hasWorkflow, projectId, rememberedWorkflowId, setLastWorkflow, workflowId]);
}
