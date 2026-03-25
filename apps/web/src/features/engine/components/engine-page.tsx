"use client";

import { useState, useTransition } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { EmptyState } from "@/components/ui/empty-state";
import { SectionCard } from "@/components/ui/section-card";
import { StatusBadge } from "@/components/ui/status-badge";
import { EngineDetailPanel } from "@/features/engine/components/engine-detail-panel";
import { resolveEngineDetailTab } from "@/features/engine/components/engine-detail-panel-support";
import {
  buildEnginePathWithParams,
  createWorkflowBoundValue,
  resolveStartWorkflowDisabledReason,
  resolveWorkflowBoundValue,
  shouldResetSelectedExecution,
  useRememberLastWorkflow,
} from "@/features/engine/components/engine-page-support";
import { EngineExportPanel } from "@/features/engine/components/engine-export-panel";
import { resolveWorkflowEventsBanner, useWorkflowEventsQuerySync, useWorkflowEventsStream } from "@/features/engine/components/engine-events-stream";
import { EngineWorkflowDebugPanel } from "@/features/engine/components/engine-workflow-debug-panel";
import { EngineWorkflowSummaryCard } from "@/features/engine/components/engine-workflow-summary-card";
import { buildWorkflowSummary } from "@/features/engine/components/engine-workflow-summary-support";
import { EngineWorkflowStatusCallout } from "@/features/engine/components/engine-workflow-status-callout";
import { PreparationStatusPanel } from "@/features/project/components/preparation-status-panel";
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
  const [workflowInputState, setWorkflowInputState] = useState(() => createWorkflowBoundValue(workflowId, workflowId));
  const [selectedExecutionState, setSelectedExecutionState] = useState(() => createWorkflowBoundValue(workflowId, ""));
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
  const selectedExecutionId = resolveWorkflowBoundValue(selectedExecutionState, workflowId, "");
  const activeSelectedExecutionId = shouldResetSelectedExecution({ executions: logExecutions, selectedExecutionId }) ? "" : selectedExecutionId;
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
      setSelectedExecutionState(createWorkflowBoundValue(result.execution_id, ""));
      setParams({ workflow: result.execution_id });
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
          <div className="flex flex-wrap gap-2">
            {workflowSummary ? (
              <>
                <StatusBadge
                  status={workflowSummary.statusTone}
                  label={workflowSummary.statusLabel}
                />
                <StatusBadge
                  status={workflowSummary.modeTone}
                  label={workflowSummary.modeLabel}
                />
              </>
            ) : null}
            <button
              className="ink-button"
              disabled={primaryActionDisabled}
              onClick={() => actionMutation.mutate(workflowControls.primary.action)}
              title={startWorkflowDisabledReason ?? undefined}
            >
              {actionMutation.isPending ? "处理中..." : workflowControls.primary.label}
            </button>
            {workflowControls.secondary.map((control) => (
              <button key={control.action} className={control.tone === "danger" ? "ink-button-danger" : "ink-button-secondary"} disabled={actionMutation.isPending || control.disabled} onClick={() => actionMutation.mutate(control.action)}>
                {control.label}
              </button>
            ))}
          </div>
        }
      >
        <div className="grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
          <div className="space-y-4">
            <label className="block space-y-2">
              <span className="label-text">当前 workflow id</span>
              <input className="ink-input" value={workflowInput} onChange={(event) => setWorkflowInputState(createWorkflowBoundValue(workflowId, event.target.value))} />
            </label>
            <div className="flex flex-wrap gap-2">
              <button
                className="ink-button-secondary"
                disabled={!workflowInput || isPending}
                onClick={() => {
                  setFeedback(null);
                  setSelectedExecutionState(createWorkflowBoundValue(workflowInput, ""));
                  setParams({ workflow: workflowInput });
                }}
              >
                载入已有 workflow
              </button>
              <button aria-haspopup="dialog" className="ink-button-secondary" disabled={!hasWorkflow} onClick={() => setParams({ export: "1" })}>
                导出成稿
              </button>
              <Link className="ink-button-secondary" href={`/workspace/project/${projectId}/studio?panel=chapter`}>
                返回 Studio
              </Link>
            </div>
            {startWorkflowDisabledReason ? <div className="rounded-2xl border border-[rgba(183,121,31,0.18)] bg-[rgba(183,121,31,0.08)] px-4 py-3 text-sm text-[var(--accent-warning)]">{startWorkflowDisabledReason}</div> : null}
            {workflowEventsBanner ? <div className="rounded-2xl bg-[rgba(183,121,31,0.1)] px-4 py-3 text-sm text-[var(--accent-warning)]">{workflowEventsBanner}</div> : null}
            {workflowEventsErrorMessage ? <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">{workflowEventsErrorMessage}</div> : null}
            <EngineWorkflowStatusCallout workflow={workflowQuery.data} onOpenTab={openEngineTab} />
            {feedback ? <div className="rounded-2xl bg-[rgba(58,124,165,0.1)] px-4 py-3 text-sm text-[var(--accent-info)]">{feedback}</div> : null}
            {workflowQuery.error ? <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">{getErrorMessage(workflowQuery.error)}</div> : null}
            {workflowQuery.data ? (
              <div className="space-y-4">
                {workflowSummary ? (
                  <EngineWorkflowSummaryCard summary={workflowSummary} />
                ) : null}
                <EngineWorkflowDebugPanel workflow={workflowQuery.data} />
              </div>
            ) : (
              <div className="space-y-4">
                <PreparationStatusPanel projectId={projectId} />
                <EmptyState
                  title="尚未载入工作流"
                  description="请先看当前准备状态；若条件已满足可直接启动，若已有 workflow id 也可手动载入。"
                  action={
                    <button
                      className="ink-button"
                      disabled={primaryActionDisabled}
                      onClick={() => actionMutation.mutate(workflowControls.primary.action)}
                      title={startWorkflowDisabledReason ?? undefined}
                    >
                      {actionMutation.isPending ? "处理中..." : workflowControls.primary.label}
                    </button>
                  }
                />
              </div>
            )}
          </div>
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
            onOpenTab={openEngineTab}
            projectId={projectId}
            replays={{
              errorMessage: promptReplayQuery.error ? getErrorMessage(promptReplayQuery.error) : null,
              executions: logExecutions,
              executionsErrorMessage: logsQuery.error ? getErrorMessage(logsQuery.error) : null,
              isExecutionsLoading: logsQuery.isPending,
              isReplaysLoading: promptReplayQuery.isPending,
              onSelectExecutionId: (value) => setSelectedExecutionState(createWorkflowBoundValue(workflowId, value)),
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
