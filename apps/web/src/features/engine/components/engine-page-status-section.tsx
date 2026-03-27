"use client";

import { EmptyState } from "@/components/ui/empty-state";
import { EngineWorkflowDebugPanel } from "@/features/engine/components/engine-workflow-debug-panel";
import { EngineWorkflowStatusCallout } from "@/features/engine/components/engine-workflow-status-callout";
import { EngineWorkflowSummaryCard } from "@/features/engine/components/engine-workflow-summary-card";
import { PreparationStatusPanel } from "@/features/project/components/preparation-status-panel";
import type { WorkflowExecution } from "@/lib/api/types";

import type { WorkflowSummaryCardData } from "./engine-workflow-summary-support";
import type { EngineTabKey } from "./engine-workflow-status-support";

type EnginePageStatusSectionProps = {
  feedback: string | null;
  isActionPending: boolean;
  onOpenTab: (tab: EngineTabKey) => void;
  onPrimaryAction: () => void;
  primaryActionDisabled: boolean;
  primaryActionLabel: string;
  projectId: string;
  startWorkflowDisabledReason: string | null;
  workflow: WorkflowExecution | undefined;
  workflowErrorMessage: string | null;
  workflowEventsBanner: string | null;
  workflowEventsErrorMessage: string | null;
  workflowSummary: WorkflowSummaryCardData | null;
};

type StatusBannerItem = {
  className: string;
  id: string;
  message: string;
};

export function EnginePageStatusSection({
  feedback,
  isActionPending,
  onOpenTab,
  onPrimaryAction,
  primaryActionDisabled,
  primaryActionLabel,
  projectId,
  startWorkflowDisabledReason,
  workflow,
  workflowErrorMessage,
  workflowEventsBanner,
  workflowEventsErrorMessage,
  workflowSummary,
}: Readonly<EnginePageStatusSectionProps>) {
  const statusBanners = [
    {
      className: "border border-[rgba(183,121,31,0.18)] bg-[rgba(183,121,31,0.08)] text-[var(--accent-warning)]",
      id: "start-disabled",
      message: startWorkflowDisabledReason,
    },
    {
      className: "bg-[rgba(183,121,31,0.1)] text-[var(--accent-warning)]",
      id: "events-banner",
      message: workflowEventsBanner,
    },
    {
      className: "bg-[rgba(178,65,46,0.12)] text-[var(--accent-danger)]",
      id: "events-error",
      message: workflowEventsErrorMessage,
    },
    {
      className: "bg-[rgba(58,124,165,0.1)] text-[var(--accent-info)]",
      id: "feedback",
      message: feedback,
    },
    {
      className: "bg-[rgba(178,65,46,0.12)] text-[var(--accent-danger)]",
      id: "workflow-error",
      message: workflowErrorMessage,
    },
  ].filter((item): item is StatusBannerItem => item.message !== null);

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
      <div className="space-y-4">
        {statusBanners.map((item) => (
          <StatusBanner key={item.id} className={item.className} message={item.message} />
        ))}
        <EngineWorkflowStatusCallout workflow={workflow} onOpenTab={onOpenTab} />
        {workflow ? (
          workflowSummary ? <EngineWorkflowSummaryCard summary={workflowSummary} /> : null
        ) : (
          <EmptyState
            title="尚未载入工作流"
            description="先确认准备状态，再启动新执行，或输入 workflow id 载入既有批次。"
            action={
              <button
                className="ink-button"
                disabled={primaryActionDisabled}
                onClick={onPrimaryAction}
                title={startWorkflowDisabledReason ?? undefined}
                type="button"
              >
                {isActionPending ? "处理中…" : primaryActionLabel}
              </button>
            }
          />
        )}
      </div>

      <aside className="space-y-4">
        {workflow ? (
          <EngineWorkflowDebugPanel workflow={workflow} />
        ) : (
          <PreparationStatusPanel projectId={projectId} />
        )}
      </aside>
    </div>
  );
}

function StatusBanner({
  className,
  message,
}: Readonly<{
  className: string;
  message: string;
}>) {
  return (
    <div aria-live="polite" className={`rounded-2xl px-4 py-3 text-sm ${className}`} role="status">
      {message}
    </div>
  );
}
