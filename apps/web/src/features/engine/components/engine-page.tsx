"use client";

import { useEffect, useState, useTransition } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { SectionCard } from "@/components/ui/section-card";
import { EngineDetailPanel } from "@/features/engine/components/engine-detail-panel";
import { EnginePageHeaderActions } from "@/features/engine/components/engine-page-header-actions";
import { EnginePageSidebar } from "@/features/engine/components/engine-page-sidebar";
import { resolveEngineDetailTab } from "@/features/engine/components/engine-detail-panel-support";
import {
  buildEnginePathWithParams,
  createWorkflowBoundValue,
  resolveExecutionParamForWorkflow,
  resolveReplayExecutionSelection,
  resolveStartWorkflowDisabledReason,
  resolveWorkflowBoundValue,
  useRememberLastWorkflow,
} from "@/features/engine/components/engine-page-support";
import { EngineExportPanel } from "@/features/engine/components/engine-export-panel";
import { resolveWorkflowEventsBanner, useWorkflowEventsQuerySync, useWorkflowEventsStream } from "@/features/engine/components/engine-events-stream";
import { buildWorkflowSummary } from "@/features/engine/components/engine-workflow-summary-support";
import { resolveEngineWorkflowControls, shouldPollWorkflow } from "@/features/engine/components/engine-workflow-controls";
import { getWorkflowBillingSummary, listWorkflowTokenUsages } from "@/lib/api/billing";
import { getErrorMessage } from "@/lib/api/client";
import { listWorkflowExecutions, listWorkflowLogs, listPromptReplays } from "@/lib/api/observability";
import { getProjectPreparationStatus } from "@/lib/api/projects";
import { getWorkflowReviewSummary, listWorkflowReviewActions } from "@/lib/api/review";
import { cancelWorkflow, getWorkflow, pauseWorkflow, resumeWorkflow, startWorkflow } from "@/lib/api/workflow";
import { useWorkspaceStore } from "@/lib/stores/workspace-store";
import type { EngineTabKey } from "@/features/engine/components/engine-workflow-status-support";

type EnginePageProps = { projectId: string };

export function EnginePage({ projectId }: EnginePageProps) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const tab = resolveEngineDetailTab(searchParams.get("tab"));
  const exportOpen = searchParams.get("export") === "1";
  const lastWorkflowByProject = useWorkspaceStore((state) => state.lastWorkflowByProject);
  const setLastWorkflow = useWorkspaceStore((state) => state.setLastWorkflow);
  const workflowId = searchParams.get("workflow") ?? lastWorkflowByProject[projectId] ?? "";
  const selectedExecutionId = searchParams.get("execution") ?? "";
  const [workflowInputState, setWorkflowInputState] = useState(() => createWorkflowBoundValue(workflowId, workflowId));
  const [feedback, setFeedback] = useState<string | null>(null);
  const workflowInput = resolveWorkflowBoundValue(workflowInputState, workflowId, workflowId);
  const setParams = (patches: Record<string, string | null>) => startTransition(() => router.replace(buildEnginePathWithParams(pathname, searchParams.toString(), patches)));

  const workflowQuery = useQuery({
    queryKey: ["workflow", workflowId],
    queryFn: () => getWorkflow(workflowId),
    enabled: Boolean(workflowId),
    refetchInterval: (query) => (shouldPollWorkflow(query.state.data?.status) ? 5000 : false),
  });
  const workflowControls = resolveEngineWorkflowControls(workflowQuery.data);
  const hasWorkflow = Boolean(workflowId && workflowQuery.data);
  const preparationQuery = useQuery({
    queryKey: ["project-preparation-status", projectId],
    queryFn: () => getProjectPreparationStatus(projectId),
    enabled: workflowControls.primary.action === "start" && !workflowControls.primary.disabled,
  });

  const reviewsQuery = useQuery({
    queryKey: ["workflow-reviews", workflowId],
    queryFn: () => Promise.all([getWorkflowReviewSummary(workflowId), listWorkflowReviewActions(workflowId)]),
    enabled: hasWorkflow && tab === "reviews",
  });
  const billingQuery = useQuery({
    queryKey: ["workflow-billing", workflowId],
    queryFn: () => Promise.all([getWorkflowBillingSummary(workflowId), listWorkflowTokenUsages(workflowId)]),
    enabled: hasWorkflow && tab === "billing",
  });
  const logsQuery = useQuery({
    queryKey: ["workflow-observability", workflowId],
    queryFn: () => Promise.all([listWorkflowExecutions(workflowId), listWorkflowLogs(workflowId)]),
    enabled: hasWorkflow && (tab === "logs" || tab === "replays" || tab === "overview"),
    refetchInterval: shouldPollWorkflow(workflowQuery.data?.status) ? 5000 : false,
  });

  const logExecutions = logsQuery.data?.[0] ?? [];
  const replayExecutionSelection = resolveReplayExecutionSelection({
    canValidateSelection:
      hasWorkflow &&
      logsQuery.data !== undefined &&
      (tab === "logs" || tab === "replays" || tab === "overview"),
    executions: logExecutions,
    selectedExecutionId,
  });
  const activeSelectedExecutionId = replayExecutionSelection.activeSelectedExecutionId;
  const promptReplayQuery = useQuery({
    queryKey: ["prompt-replays", workflowId, activeSelectedExecutionId],
    queryFn: () => listPromptReplays(workflowId, activeSelectedExecutionId),
    enabled: hasWorkflow && tab === "replays" && Boolean(activeSelectedExecutionId),
  });

  const actionMutation = useMutation({
    mutationFn: async (action: "start" | "pause" | "resume" | "cancel") => {
      if (action === "start") {
        return startWorkflow(projectId);
      }
      if (action === "pause") {
        return pauseWorkflow(workflowId);
      }
      if (action === "resume") {
        return resumeWorkflow(workflowId);
      }
      return cancelWorkflow(workflowId);
    },
    onSuccess: (result) => {
      setFeedback("工作流状态已更新。");
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
    onError: (error) => setFeedback(getErrorMessage(error)),
  });

  const selectedExecution = logExecutions.find((item) => item.id === activeSelectedExecutionId) ?? null;
  const workflowEvents = useWorkflowEventsStream({
    workflowId,
    enabled: hasWorkflow && shouldPollWorkflow(workflowQuery.data?.status),
    snapshotLogs: logsQuery.data?.[1] ?? [],
  });

  useRememberLastWorkflow({
    hasWorkflow,
    projectId,
    rememberedWorkflowId: lastWorkflowByProject[projectId],
    setLastWorkflow,
    workflowId,
  });

  useEffect(() => {
    if (!replayExecutionSelection.shouldClearExecutionParam) {
      return;
    }
    startTransition(() => {
      router.replace(
        buildEnginePathWithParams(pathname, searchParams.toString(), { execution: null }),
      );
    });
  }, [
    pathname,
    replayExecutionSelection.shouldClearExecutionParam,
    router,
    searchParams,
    startTransition,
  ]);

  const executionLogs = workflowEvents.logs;
  const reviewSummary = reviewsQuery.data?.[0] ?? null;
  const reviewActions = reviewsQuery.data?.[1] ?? [];
  const billingSummary = billingQuery.data?.[0] ?? null;
  const billingUsages = billingQuery.data?.[1] ?? [];
  const workflowEventsBanner = resolveWorkflowEventsBanner(workflowEvents.connectionState);
  const workflowEventsErrorMessage = workflowEvents.clientErrorMessage;
  const startWorkflowDisabledReason = resolveStartWorkflowDisabledReason({
    action: workflowControls.primary.action,
    errorMessage: preparationQuery.error ? getErrorMessage(preparationQuery.error) : null,
    isLoading: preparationQuery.isLoading,
    preparation: preparationQuery.data,
  });
  const workflowSummary = buildWorkflowSummary(workflowQuery.data);
  const primaryActionDisabled =
    actionMutation.isPending ||
    workflowControls.primary.disabled ||
    Boolean(startWorkflowDisabledReason);
  const openEngineTab = (nextTab: EngineTabKey) => setParams({ tab: nextTab });
  const openReplayExecution = (executionId: string) =>
    setParams({ execution: executionId, tab: "replays" });

  useWorkflowEventsQuerySync({
    workflowId,
    reconnectSignal: workflowEvents.reconnectSignal,
    endSignal: workflowEvents.endSignal,
  });

  return (
    <div className="space-y-6">
      <SectionCard
        title="Engine"
        description="执行控制台优先回答三个问题：现在在跑什么、为何暂停、是否可以继续。"
        action={
          <EnginePageHeaderActions
            isActionPending={actionMutation.isPending}
            onAction={(action) => actionMutation.mutate(action)}
            primaryAction={workflowControls.primary}
            primaryActionDisabled={primaryActionDisabled}
            secondaryControls={workflowControls.secondary}
            startWorkflowDisabledReason={startWorkflowDisabledReason}
            workflowSummary={workflowSummary}
          />
        }
      >
        <div className="grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
          <EnginePageSidebar
            feedback={feedback}
            hasWorkflow={hasWorkflow}
            isActionPending={actionMutation.isPending}
            isLoadWorkflowDisabled={!workflowInput || isPending}
            onLoadWorkflow={() => {
              setFeedback(null);
              setParams({
                execution: resolveExecutionParamForWorkflow({
                  currentExecutionId: selectedExecutionId,
                  currentWorkflowId: workflowId,
                  nextWorkflowId: workflowInput,
                }),
                workflow: workflowInput,
              });
            }}
            onOpenExport={() => setParams({ export: "1" })}
            onOpenTab={openEngineTab}
            onPrimaryAction={() => actionMutation.mutate(workflowControls.primary.action)}
            onWorkflowInputChange={(value) =>
              setWorkflowInputState(createWorkflowBoundValue(workflowId, value))
            }
            primaryActionDisabled={primaryActionDisabled}
            primaryActionLabel={workflowControls.primary.label}
            projectId={projectId}
            startWorkflowDisabledReason={startWorkflowDisabledReason}
            workflow={workflowQuery.data}
            workflowErrorMessage={
              workflowQuery.error ? getErrorMessage(workflowQuery.error) : null
            }
            workflowEventsBanner={workflowEventsBanner}
            workflowEventsErrorMessage={workflowEventsErrorMessage}
            workflowInput={workflowInput}
            workflowSummary={workflowSummary}
          />
          <EngineDetailPanel
            activeTab={tab}
            billing={{
              errorMessage: billingQuery.error ? getErrorMessage(billingQuery.error) : null,
              isLoading: billingQuery.isPending,
              summary: billingSummary,
              usages: billingUsages,
            }}
            context={{ projectId, workflowId }}
            hasWorkflow={hasWorkflow}
            logs={{
              errorMessage: logsQuery.error ? getErrorMessage(logsQuery.error) : null,
              executions: logExecutions,
              executionLogs,
              isLoading: logsQuery.isPending,
            }}
            onOpenReplayExecution={openReplayExecution}
            onOpenTab={openEngineTab}
            projectId={projectId}
            replays={{
              errorMessage: promptReplayQuery.error ? getErrorMessage(promptReplayQuery.error) : null,
              executions: logExecutions,
              executionsErrorMessage: logsQuery.error ? getErrorMessage(logsQuery.error) : null,
              isExecutionsLoading: logsQuery.isPending,
              isReplaysLoading: promptReplayQuery.isPending,
              onSelectExecutionId: (value) => setParams({ execution: value || null }),
              replays: promptReplayQuery.data ?? [],
              selectedExecution,
              selectedExecutionId: activeSelectedExecutionId,
            }}
            reviews={{
              actions: reviewActions,
              errorMessage: reviewsQuery.error ? getErrorMessage(reviewsQuery.error) : null,
              isLoading: reviewsQuery.isPending,
              summary: reviewSummary,
            }}
            workflow={workflowQuery.data}
          />
        </div>
      </SectionCard>
      {exportOpen ? <EngineExportPanel onClose={() => setParams({ export: null })} projectId={projectId} workflowId={workflowId} /> : null}
    </div>
  );
}
