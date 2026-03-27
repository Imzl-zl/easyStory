"use client";

import Link from "next/link";

import { StatusBadge } from "@/components/ui/status-badge";

import type { EngineWorkflowControl, WorkflowAction } from "./engine-workflow-controls";
import type { WorkflowSummaryCardData } from "./engine-workflow-summary-support";

type EnginePageHeaderProps = {
  hasWorkflow: boolean;
  isActionPending: boolean;
  isLoadWorkflowDisabled: boolean;
  onAction: (action: WorkflowAction) => void;
  onLoadWorkflow: () => void;
  onOpenExport: () => void;
  onWorkflowInputChange: (value: string) => void;
  primaryAction: EngineWorkflowControl;
  primaryActionDisabled: boolean;
  projectId: string;
  secondaryControls: EngineWorkflowControl[];
  startWorkflowDisabledReason: string | null;
  workflowInput: string;
  workflowSummary: WorkflowSummaryCardData | null;
};

export function EnginePageHeader({
  hasWorkflow,
  isActionPending,
  isLoadWorkflowDisabled,
  onAction,
  onLoadWorkflow,
  onOpenExport,
  onWorkflowInputChange,
  primaryAction,
  primaryActionDisabled,
  projectId,
  secondaryControls,
  startWorkflowDisabledReason,
  workflowInput,
  workflowSummary,
}: Readonly<EnginePageHeaderProps>) {
  return (
    <section className="panel-shell p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.28em] text-[var(--accent-ink)]">引擎</p>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="font-serif text-3xl font-semibold text-[var(--text-primary)]">
              工作流控制
            </h1>
            {workflowSummary ? (
              <>
                <StatusBadge status={workflowSummary.statusTone} label={workflowSummary.statusLabel} />
                <StatusBadge status={workflowSummary.modeTone} label={workflowSummary.modeLabel} />
              </>
            ) : null}
          </div>
          <p className="max-w-3xl text-sm leading-6 text-[var(--text-secondary)]">
            {workflowSummary?.workflowIdentity ?? "载入已有 workflow，或在准备状态就绪后启动新的执行批次。"}
          </p>
        </div>
        <EnginePagePrimaryActions
          isActionPending={isActionPending}
          onAction={onAction}
          primaryAction={primaryAction}
          primaryActionDisabled={primaryActionDisabled}
          secondaryControls={secondaryControls}
          startWorkflowDisabledReason={startWorkflowDisabledReason}
        />
      </div>

      <div className="mt-6 grid gap-4 border-t border-[var(--line-soft)] pt-5 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-end">
        <label className="block space-y-2">
          <span className="label-text">工作流 ID</span>
          <input
            className="ink-input"
            placeholder="输入 workflow id 以载入已有执行"
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
            返回工作室
          </Link>
        </div>
      </div>
    </section>
  );
}

function EnginePagePrimaryActions({
  isActionPending,
  onAction,
  primaryAction,
  primaryActionDisabled,
  secondaryControls,
  startWorkflowDisabledReason,
}: Readonly<{
  isActionPending: boolean;
  onAction: (action: WorkflowAction) => void;
  primaryAction: EngineWorkflowControl;
  primaryActionDisabled: boolean;
  secondaryControls: EngineWorkflowControl[];
  startWorkflowDisabledReason: string | null;
}>) {
  return (
    <div className="flex flex-wrap gap-2">
      <button
        className="ink-button"
        disabled={primaryActionDisabled}
        onClick={() => onAction(primaryAction.action)}
        title={startWorkflowDisabledReason ?? undefined}
        type="button"
      >
        {isActionPending ? "处理中..." : primaryAction.label}
      </button>
      {secondaryControls.map((control) => (
        <button
          key={control.action}
          className={control.tone === "danger" ? "ink-button-danger" : "ink-button-secondary"}
          disabled={isActionPending || control.disabled}
          onClick={() => onAction(control.action)}
          type="button"
        >
          {control.label}
        </button>
      ))}
    </div>
  );
}
