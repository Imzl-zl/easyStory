"use client";

import { useState, useTransition } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { CodeBlock } from "@/components/ui/code-block";
import { EmptyState } from "@/components/ui/empty-state";
import { SectionCard } from "@/components/ui/section-card";
import { StatusBadge } from "@/components/ui/status-badge";
import { EngineBillingPanel } from "@/features/engine/components/engine-billing-panel";
import { EngineBlock } from "@/features/engine/components/engine-block";
import { EngineContextPanel } from "@/features/engine/components/engine-context-panel";
import {
  buildEnginePathWithParams,
  createWorkflowBoundValue,
  resolveWorkflowBoundValue,
  shouldResetSelectedExecution,
  useRememberLastWorkflow,
} from "@/features/engine/components/engine-page-support";
import { EngineExportPanel } from "@/features/engine/components/engine-export-panel";
import { resolveWorkflowEventsBanner, useWorkflowEventsQuerySync, useWorkflowEventsStream } from "@/features/engine/components/engine-events-stream";
import { EngineLogsPanel } from "@/features/engine/components/engine-logs-panel";
import { EngineReplayPanel } from "@/features/engine/components/engine-replay-panel";
import { EngineReviewPanel } from "@/features/engine/components/engine-review-panel";
import { EngineTaskPanel } from "@/features/engine/components/engine-task-panel";
import { resolveEngineWorkflowControls, shouldPollWorkflow } from "@/features/engine/components/engine-workflow-controls";
import { getWorkflowBillingSummary, listWorkflowTokenUsages } from "@/lib/api/billing";
import { getErrorMessage } from "@/lib/api/client";
import { listWorkflowExecutions, listWorkflowLogs, listPromptReplays } from "@/lib/api/observability";
import { getWorkflowReviewSummary, listWorkflowReviewActions } from "@/lib/api/review";
import { cancelWorkflow, getWorkflow, pauseWorkflow, resumeWorkflow, startWorkflow } from "@/lib/api/workflow";
import { useWorkspaceStore } from "@/lib/stores/workspace-store";

const TABS = ["overview", "tasks", "reviews", "billing", "logs", "context", "replays"] as const;

type EnginePageProps = { projectId: string };

export function EnginePage({ projectId }: EnginePageProps) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const tab = (searchParams.get("tab") ?? "overview") as (typeof TABS)[number];
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
            {workflowQuery.data ? <StatusBadge status={workflowQuery.data.status} /> : null}
            <button className="ink-button" disabled={actionMutation.isPending || workflowControls.primary.disabled} onClick={() => actionMutation.mutate(workflowControls.primary.action)}>
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
            {workflowEventsBanner ? <div className="rounded-2xl bg-[rgba(183,121,31,0.1)] px-4 py-3 text-sm text-[var(--accent-warning)]">{workflowEventsBanner}</div> : null}
            {workflowEventsErrorMessage ? <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">{workflowEventsErrorMessage}</div> : null}
            {feedback ? <div className="rounded-2xl bg-[rgba(58,124,165,0.1)] px-4 py-3 text-sm text-[var(--accent-info)]">{feedback}</div> : null}
            {workflowQuery.error ? <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">{getErrorMessage(workflowQuery.error)}</div> : null}
            {workflowQuery.data ? <CodeBlock value={workflowQuery.data} /> : <EmptyState title="尚未载入工作流" description="先启动工作流，或输入已有 workflow id 后载入。" />}
          </div>
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {TABS.map((item) => (
                <button key={item} className="ink-tab" data-active={tab === item} onClick={() => setParams({ tab: item })}>
                  {item}
                </button>
              ))}
            </div>
            {tab === "overview" ? <EngineBlock title="执行概览"><CodeBlock value={logExecutions.length > 0 ? logExecutions : workflowQuery.data?.nodes ?? []} /></EngineBlock> : null}
            {tab === "tasks" ? <EngineBlock title="章节任务"><EngineTaskPanel key={workflowId || "workflow-empty"} projectId={projectId} workflow={workflowQuery.data} /></EngineBlock> : null}
            {tab === "reviews" ? <EngineBlock title="审核摘要与动作"><EngineReviewPanel summary={reviewSummary} actions={reviewActions} isLoading={reviewsQuery.isPending} errorMessage={reviewsQuery.error ? getErrorMessage(reviewsQuery.error) : null} /></EngineBlock> : null}
            {tab === "billing" ? <EngineBlock title="账单摘要与 Token 使用"><EngineBillingPanel summary={billingSummary} usages={billingUsages} isLoading={billingQuery.isPending} errorMessage={billingQuery.error ? getErrorMessage(billingQuery.error) : null} /></EngineBlock> : null}
            {tab === "logs" ? <EngineBlock title="节点执行与日志"><EngineLogsPanel executions={logExecutions} logs={executionLogs} isLoading={logsQuery.isPending} errorMessage={logsQuery.error ? getErrorMessage(logsQuery.error) : null} /></EngineBlock> : null}
            {tab === "context" ? <EngineBlock title="上下文预览"><EngineContextPanel projectId={projectId} workflowId={workflowId} isWorkflowReady={hasWorkflow} /></EngineBlock> : null}
            {tab === "replays" ? <EngineBlock title="Prompt 回放"><EngineReplayPanel isWorkflowReady={hasWorkflow} executions={logExecutions} selectedExecutionId={activeSelectedExecutionId} onSelectExecutionId={(value) => setSelectedExecutionState(createWorkflowBoundValue(workflowId, value))} selectedExecution={selectedExecution} replays={promptReplayQuery.data ?? []} isExecutionsLoading={logsQuery.isPending} isReplaysLoading={promptReplayQuery.isPending} executionsErrorMessage={logsQuery.error ? getErrorMessage(logsQuery.error) : null} replaysErrorMessage={promptReplayQuery.error ? getErrorMessage(promptReplayQuery.error) : null} /></EngineBlock> : null}
          </div>
        </div>
      </SectionCard>
      {exportOpen ? <EngineExportPanel onClose={() => setParams({ export: null })} projectId={projectId} workflowId={workflowId} /> : null}
    </div>
  );
}
