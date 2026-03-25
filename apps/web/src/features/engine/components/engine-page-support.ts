"use client";

import { useEffect } from "react";

import type { NodeExecutionView } from "@/lib/api/types";

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
