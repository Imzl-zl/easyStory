"use client";

import Link from "next/link";

import { EmptyState } from "@/components/ui/empty-state";
import { EngineWorkflowDebugPanel } from "@/features/engine/components/engine-workflow-debug-panel";
import { EngineWorkflowSummaryCard } from "@/features/engine/components/engine-workflow-summary-card";
import { EngineWorkflowStatusCallout } from "@/features/engine/components/engine-workflow-status-callout";
import { PreparationStatusPanel } from "@/features/project/components/preparation-status-panel";
import type { WorkflowExecution } from "@/lib/api/types";

import type { WorkflowSummaryCardData } from "./engine-workflow-summary-support";
import type { EngineTabKey } from "./engine-workflow-status-support";

type EnginePageSidebarProps = {
  feedback: string | null;
  hasWorkflow: boolean;
  isActionPending: boolean;
  isLoadWorkflowDisabled: boolean;
  onLoadWorkflow: () => void;
  onOpenExport: () => void;
  onOpenTab: (tab: EngineTabKey) => void;
  onPrimaryAction: () => void;
  onWorkflowInputChange: (value: string) => void;
  primaryActionDisabled: boolean;
  primaryActionLabel: string;
  projectId: string;
  startWorkflowDisabledReason: string | null;
  workflow: WorkflowExecution | undefined;
  workflowErrorMessage: string | null;
  workflowEventsBanner: string | null;
  workflowEventsErrorMessage: string | null;
  workflowInput: string;
  workflowSummary: WorkflowSummaryCardData | null;
};

export function EnginePageSidebar({
  feedback,
  hasWorkflow,
  isActionPending,
  isLoadWorkflowDisabled,
  onLoadWorkflow,
  onOpenExport,
  onOpenTab,
  onPrimaryAction,
  onWorkflowInputChange,
  primaryActionDisabled,
  primaryActionLabel,
  projectId,
  startWorkflowDisabledReason,
  workflow,
  workflowErrorMessage,
  workflowEventsBanner,
  workflowEventsErrorMessage,
  workflowInput,
  workflowSummary,
}: Readonly<EnginePageSidebarProps>) {
  return (
    <div className="space-y-4">
      <label className="block space-y-2">
        <span className="label-text">当前 workflow id</span>
        <input
          className="ink-input"
          value={workflowInput}
          onChange={(event) => onWorkflowInputChange(event.target.value)}
        />
      </label>
      <div className="flex flex-wrap gap-2">
        <button
          className="ink-button-secondary"
          disabled={isLoadWorkflowDisabled}
          onClick={onLoadWorkflow}
          type="button"
        >
          载入已有 workflow
        </button>
        <button
          aria-haspopup="dialog"
          className="ink-button-secondary"
          disabled={!hasWorkflow}
          onClick={onOpenExport}
          type="button"
        >
          导出成稿
        </button>
        <Link
          className="ink-button-secondary"
          href={`/workspace/project/${projectId}/studio?panel=chapter`}
        >
          返回 Studio
        </Link>
      </div>
      {startWorkflowDisabledReason ? (
        <SidebarBanner
          className="border border-[rgba(183,121,31,0.18)] bg-[rgba(183,121,31,0.08)] text-[var(--accent-warning)]"
          message={startWorkflowDisabledReason}
        />
      ) : null}
      {workflowEventsBanner ? (
        <SidebarBanner
          className="bg-[rgba(183,121,31,0.1)] text-[var(--accent-warning)]"
          message={workflowEventsBanner}
        />
      ) : null}
      {workflowEventsErrorMessage ? (
        <SidebarBanner
          className="bg-[rgba(178,65,46,0.12)] text-[var(--accent-danger)]"
          message={workflowEventsErrorMessage}
        />
      ) : null}
      <EngineWorkflowStatusCallout workflow={workflow} onOpenTab={onOpenTab} />
      {feedback ? (
        <SidebarBanner
          className="bg-[rgba(58,124,165,0.1)] text-[var(--accent-info)]"
          message={feedback}
        />
      ) : null}
      {workflowErrorMessage ? (
        <SidebarBanner
          className="bg-[rgba(178,65,46,0.12)] text-[var(--accent-danger)]"
          message={workflowErrorMessage}
        />
      ) : null}
      {workflow ? (
        <div className="space-y-4">
          {workflowSummary ? <EngineWorkflowSummaryCard summary={workflowSummary} /> : null}
          <EngineWorkflowDebugPanel workflow={workflow} />
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
                onClick={onPrimaryAction}
                title={startWorkflowDisabledReason ?? undefined}
                type="button"
              >
                {isActionPending ? "处理中..." : primaryActionLabel}
              </button>
            }
          />
        </div>
      )}
    </div>
  );
}

function SidebarBanner({
  className,
  message,
}: Readonly<{
  className: string;
  message: string;
}>) {
  return <div className={`rounded-2xl px-4 py-3 text-sm ${className}`}>{message}</div>;
}
