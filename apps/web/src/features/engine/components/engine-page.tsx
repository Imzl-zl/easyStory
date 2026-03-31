"use client";

import { useState, useTransition } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { getErrorMessage } from "@/lib/api/client";
import { useWorkspaceStore } from "@/lib/stores/workspace-store";

import { EngineDetailPanel } from "./engine-detail-panel";
import { EngineExportPanel } from "./engine-export-panel";
import {
  resolveWorkflowEventsBanner,
  useWorkflowEventsQuerySync,
  useWorkflowEventsStream,
} from "./engine-events-stream";
import {
  buildBillingState,
  buildEngineBanners,
  buildLogsState,
  buildReplayState,
  buildReviewsState,
  shouldInspectLogs,
  useBillingQuery,
  useClearInvalidExecutionParam,
  useLogsQuery,
  usePreparationQuery,
  usePromptReplayQuery,
  useReviewsQuery,
  useWorkflowActionMutation,
  useWorkflowQuery,
} from "./engine-page-model";
import { EnginePageShell } from "./engine-page-shell";
import {
  buildEnginePathWithParams,
  createWorkflowBoundValue,
  resolveExecutionParamForWorkflow,
  resolveReplayExecutionSelection,
  resolveStartWorkflowDisabledReason,
  resolveWorkflowBoundValue,
  useRememberLastWorkflow,
} from "./engine-page-support";
import { resolveEngineDetailTab } from "./engine-detail-panel-support";
import { buildWorkflowSummary } from "./engine-workflow-summary-support";
import { resolveEngineWorkflowControls, shouldPollWorkflow } from "./engine-workflow-controls";
import type { EngineTabKey } from "./engine-workflow-status-support";

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
  const workflowInput = resolveWorkflowBoundValue(workflowInputState, workflowId, workflowId);
  const setParams = (patches: Record<string, string | null>) =>
    startTransition(() => router.replace(buildEnginePathWithParams(pathname, searchParams.toString(), patches)));

  const workflowQuery = useWorkflowQuery(workflowId);
  const workflowControls = resolveEngineWorkflowControls(workflowQuery.data);
  const hasWorkflow = Boolean(workflowId && workflowQuery.data);
  const preparationQuery = usePreparationQuery(projectId, workflowControls.primary.action, workflowControls.primary.disabled);
  const reviewsQuery = useReviewsQuery(hasWorkflow, tab, workflowId);
  const billingQuery = useBillingQuery(hasWorkflow, tab, workflowId);
  const logsQuery = useLogsQuery(hasWorkflow, tab, workflowId, workflowQuery.data?.status);
  const logExecutions = logsQuery.data?.[0] ?? [];
  const replaySelection = resolveReplayExecutionSelection({
    canValidateSelection: hasWorkflow && logsQuery.data !== undefined && shouldInspectLogs(tab),
    executions: logExecutions,
    selectedExecutionId,
  });
  const activeSelectedExecutionId = replaySelection.activeSelectedExecutionId;
  const promptReplayQuery = usePromptReplayQuery(activeSelectedExecutionId, hasWorkflow, tab, workflowId);
  const actionMutation = useWorkflowActionMutation({
    projectId,
    queryClient,
    selectedExecutionId,
    setLastWorkflow,
    setParams,
    setWorkflowInputState,
    workflowId,
  });
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
  useClearInvalidExecutionParam({
    pathname,
    router,
    searchParams,
    shouldClear: replaySelection.shouldClearExecutionParam,
    startTransition,
  });
  useWorkflowEventsQuerySync({
    workflowId,
    reconnectSignal: workflowEvents.reconnectSignal,
    endSignal: workflowEvents.endSignal,
  });

  const workflowSummary = buildWorkflowSummary(workflowQuery.data);
  const startWorkflowDisabledReason = resolveStartWorkflowDisabledReason({
    action: workflowControls.primary.action,
    errorMessage: preparationQuery.error ? getErrorMessage(preparationQuery.error) : null,
    isLoading: preparationQuery.isLoading,
    preparation: preparationQuery.data,
  });
  const primaryActionDisabled = actionMutation.isPending || workflowControls.primary.disabled || Boolean(startWorkflowDisabledReason);

  return (
    <>
      <EnginePageShell
        banners={buildEngineBanners({
          startWorkflowDisabledReason,
          workflowErrorMessage: workflowQuery.error ? getErrorMessage(workflowQuery.error) : null,
          workflowEventsBanner: resolveWorkflowEventsBanner(workflowEvents.connectionState),
          workflowEventsErrorMessage: workflowEvents.clientErrorMessage,
        })}
        detailPanel={(
          <EngineDetailPanel
            activeTab={tab}
            billing={buildBillingState(billingQuery)}
            context={{ projectId, workflowId }}
            hasWorkflow={hasWorkflow}
            logs={buildLogsState(logExecutions, logsQuery, workflowEvents.logs)}
            onOpenReplayExecution={(executionId) => setParams({ execution: executionId, tab: "replays" })}
            onOpenTab={(nextTab) => setParams({ tab: nextTab })}
            projectId={projectId}
            replays={buildReplayState({
              activeSelectedExecutionId,
              logExecutions,
              logsQuery,
              promptReplayQuery,
              selectedExecutionId: activeSelectedExecutionId,
              setParams,
            })}
            reviews={buildReviewsState(reviewsQuery)}
            workflow={workflowQuery.data}
          />
        )}
        hasWorkflow={hasWorkflow}
        isActionPending={actionMutation.isPending}
        isLoadWorkflowDisabled={!workflowInput || isPending}
        onAction={(action) => actionMutation.mutate(action)}
        onLoadWorkflow={() =>
          setParams({
            execution: resolveExecutionParamForWorkflow({
              currentExecutionId: selectedExecutionId,
              currentWorkflowId: workflowId,
              nextWorkflowId: workflowInput,
            }),
            workflow: workflowInput,
          })
        }
        onOpenExport={() => setParams({ export: "1" })}
        onOpenTab={(nextTab: EngineTabKey) => setParams({ tab: nextTab })}
        onWorkflowInputChange={(value) => setWorkflowInputState(createWorkflowBoundValue(workflowId, value))}
        primaryAction={workflowControls.primary}
        primaryActionDisabled={primaryActionDisabled}
        projectId={projectId}
        secondaryControls={workflowControls.secondary}
        startWorkflowDisabledReason={startWorkflowDisabledReason}
        workflow={workflowQuery.data}
        workflowInput={workflowInput}
        workflowSummary={workflowSummary}
      />
      {exportOpen ? (
        <EngineExportPanel
          onClose={() => setParams({ export: null })}
          projectId={projectId}
          workflowId={workflowId}
        />
      ) : null}
    </>
  );
}
