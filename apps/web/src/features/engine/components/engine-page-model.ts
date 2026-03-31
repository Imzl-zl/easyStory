"use client";

import { useEffect } from "react";
import type { Dispatch, SetStateAction, TransitionStartFunction } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";
import type { AppRouterInstance } from "next/dist/shared/lib/app-router-context.shared-runtime";
import type { ReadonlyURLSearchParams } from "next/navigation";

import { showAppNotice } from "@/components/ui/app-notice";
import { getWorkflowBillingSummary, listWorkflowTokenUsages } from "@/lib/api/billing";
import { getErrorMessage } from "@/lib/api/client";
import { listWorkflowExecutions, listWorkflowLogs, listPromptReplays } from "@/lib/api/observability";
import { getProjectPreparationStatus } from "@/lib/api/projects";
import { getWorkflowReviewSummary, listWorkflowReviewActions } from "@/lib/api/review";
import { cancelWorkflow, getWorkflow, pauseWorkflow, resumeWorkflow, startWorkflow } from "@/lib/api/workflow";

import { buildEnginePathWithParams, createWorkflowBoundValue, resolveExecutionParamForWorkflow } from "./engine-page-support";
import type { EngineTabKey } from "./engine-workflow-status-support";
import type { WorkflowAction } from "./engine-workflow-controls";

export function useWorkflowQuery(workflowId: string) {
  return useQuery({
    queryKey: ["workflow", workflowId],
    queryFn: () => getWorkflow(workflowId),
    enabled: Boolean(workflowId),
    refetchInterval: (query) => (shouldPollStatus(query.state.data?.status) ? 5000 : false),
  });
}

export function usePreparationQuery(projectId: string, action: string, disabled: boolean | undefined) {
  return useQuery({
    queryKey: ["project-preparation-status", projectId],
    queryFn: () => getProjectPreparationStatus(projectId),
    enabled: action === "start" && !disabled,
  });
}

export function useReviewsQuery(hasWorkflow: boolean, tab: EngineTabKey, workflowId: string) {
  return useQuery({
    queryKey: ["workflow-reviews", workflowId],
    queryFn: () => Promise.all([getWorkflowReviewSummary(workflowId), listWorkflowReviewActions(workflowId)]),
    enabled: hasWorkflow && tab === "reviews",
  });
}

export function useBillingQuery(hasWorkflow: boolean, tab: EngineTabKey, workflowId: string) {
  return useQuery({
    queryKey: ["workflow-billing", workflowId],
    queryFn: () => Promise.all([getWorkflowBillingSummary(workflowId), listWorkflowTokenUsages(workflowId)]),
    enabled: hasWorkflow && tab === "billing",
  });
}

export function useLogsQuery(hasWorkflow: boolean, tab: EngineTabKey, workflowId: string, status: string | undefined) {
  return useQuery({
    queryKey: ["workflow-observability", workflowId],
    queryFn: () => Promise.all([listWorkflowExecutions(workflowId), listWorkflowLogs(workflowId)]),
    enabled: hasWorkflow && shouldInspectLogs(tab),
    refetchInterval: shouldPollStatus(status) ? 5000 : false,
  });
}

export function usePromptReplayQuery(activeSelectedExecutionId: string, hasWorkflow: boolean, tab: EngineTabKey, workflowId: string) {
  return useQuery({
    queryKey: ["prompt-replays", workflowId, activeSelectedExecutionId],
    queryFn: () => listPromptReplays(workflowId, activeSelectedExecutionId),
    enabled: hasWorkflow && tab === "replays" && Boolean(activeSelectedExecutionId),
  });
}

export function useClearInvalidExecutionParam({
  pathname,
  router,
  searchParams,
  shouldClear,
  startTransition,
}: Readonly<{
  pathname: string;
  router: AppRouterInstance;
  searchParams: ReadonlyURLSearchParams;
  shouldClear: boolean;
  startTransition: TransitionStartFunction;
}>) {
  useEffect(() => {
    if (!shouldClear) {
      return;
    }
    startTransition(() => {
      router.replace(buildEnginePathWithParams(pathname, searchParams.toString(), { execution: null }));
    });
  }, [pathname, router, searchParams, shouldClear, startTransition]);
}

export function useWorkflowActionMutation({
  projectId,
  queryClient,
  selectedExecutionId,
  setLastWorkflow,
  setParams,
  setWorkflowInputState,
  workflowId,
}: Readonly<{
  projectId: string;
  queryClient: QueryClient;
  selectedExecutionId: string;
  setLastWorkflow: (projectId: string, workflowId: string) => void;
  setParams: (patches: Record<string, string | null>) => void;
  setWorkflowInputState: Dispatch<SetStateAction<ReturnType<typeof createWorkflowBoundValue<string>>>>;
  workflowId: string;
}>) {
  return useMutation({
    mutationFn: async (action: WorkflowAction) => {
      if (action === "start") return startWorkflow(projectId);
      if (action === "pause") return pauseWorkflow(workflowId);
      if (action === "resume") return resumeWorkflow(workflowId);
      return cancelWorkflow(workflowId);
    },
    onSuccess: (result, action) => {
      showAppNotice({ content: resolveWorkflowActionNoticeMessage(action), title: "工作流", tone: "success" });
      setLastWorkflow(projectId, result.execution_id);
      setWorkflowInputState(createWorkflowBoundValue(result.execution_id, result.execution_id));
      setParams({
        execution: resolveExecutionParamForWorkflow({
          currentExecutionId: selectedExecutionId,
          currentWorkflowId: workflowId,
          nextWorkflowId: result.execution_id,
        }),
        workflow: result.execution_id,
      });
      queryClient.invalidateQueries({ queryKey: ["workflow"] });
      queryClient.invalidateQueries({ queryKey: ["workflow-tasks"] });
      queryClient.invalidateQueries({ queryKey: ["workflow-observability"] });
      queryClient.invalidateQueries({ queryKey: ["project-preparation-status", projectId] });
    },
    onError: (error) =>
      showAppNotice({ content: getErrorMessage(error), title: "工作流", tone: "danger" }),
  });
}

export function buildReviewsState(query: ReturnType<typeof useReviewsQuery>) {
  return {
    actions: query.data?.[1] ?? [],
    errorMessage: query.error ? getErrorMessage(query.error) : null,
    isLoading: query.isPending,
    summary: query.data?.[0] ?? null,
  };
}

export function buildBillingState(query: ReturnType<typeof useBillingQuery>) {
  return {
    errorMessage: query.error ? getErrorMessage(query.error) : null,
    isLoading: query.isPending,
    summary: query.data?.[0] ?? null,
    usages: query.data?.[1] ?? [],
  };
}

export function buildLogsState(
  logExecutions: Awaited<ReturnType<typeof listWorkflowExecutions>>,
  query: ReturnType<typeof useLogsQuery>,
  executionLogs: Awaited<ReturnType<typeof listWorkflowLogs>>,
) {
  return {
    errorMessage: query.error ? getErrorMessage(query.error) : null,
    executions: logExecutions,
    executionLogs,
    isLoading: query.isPending,
  };
}

export function buildReplayState({
  activeSelectedExecutionId,
  logExecutions,
  logsQuery,
  promptReplayQuery,
  selectedExecutionId,
  setParams,
}: Readonly<{
  activeSelectedExecutionId: string;
  logExecutions: Awaited<ReturnType<typeof listWorkflowExecutions>>;
  logsQuery: ReturnType<typeof useLogsQuery>;
  promptReplayQuery: ReturnType<typeof usePromptReplayQuery>;
  selectedExecutionId: string;
  setParams: (patches: Record<string, string | null>) => void;
}>) {
  return {
    errorMessage: promptReplayQuery.error ? getErrorMessage(promptReplayQuery.error) : null,
    executions: logExecutions,
    executionsErrorMessage: logsQuery.error ? getErrorMessage(logsQuery.error) : null,
    isExecutionsLoading: logsQuery.isPending,
    isReplaysLoading: promptReplayQuery.isPending,
    onSelectExecutionId: (value: string) => setParams({ execution: value || null }),
    replays: promptReplayQuery.data ?? [],
    selectedExecution: logExecutions.find((item) => item.id === activeSelectedExecutionId) ?? null,
    selectedExecutionId,
  };
}

export function buildEngineBanners({
  startWorkflowDisabledReason,
  workflowErrorMessage,
  workflowEventsBanner,
  workflowEventsErrorMessage,
}: Readonly<{
  startWorkflowDisabledReason: string | null;
  workflowErrorMessage: string | null;
  workflowEventsBanner: string | null;
  workflowEventsErrorMessage: string | null;
}>) {
  return [
    createBanner("start-disabled", "warning", startWorkflowDisabledReason),
    createBanner("events-banner", "warning", workflowEventsBanner),
    createBanner("events-error", "danger", workflowEventsErrorMessage),
    createBanner("workflow-error", "danger", workflowErrorMessage),
  ].flatMap((item) => (item ? [item] : []));
}

export function shouldInspectLogs(tab: EngineTabKey) {
  return tab === "logs" || tab === "replays" || tab === "overview";
}

function createBanner(id: string, tone: "danger" | "warning", message: string | null) {
  return message ? { id, message, tone } : null;
}

function shouldPollStatus(status: string | undefined) {
  return status === "created" || status === "running" || status === "paused";
}

function resolveWorkflowActionNoticeMessage(action: WorkflowAction) {
  if (action === "start") return "工作流已启动。";
  if (action === "pause") return "工作流已暂停。";
  if (action === "resume") return "工作流已恢复。";
  return "工作流已取消。";
}
