"use client";

import { StatusBadge } from "@/components/ui/status-badge";

import type { EngineWorkflowControl, WorkflowAction } from "./engine-workflow-controls";
import type { WorkflowSummaryCardData } from "./engine-workflow-summary-support";

type EnginePageHeaderActionsProps = {
  isActionPending: boolean;
  onAction: (action: WorkflowAction) => void;
  primaryActionDisabled: boolean;
  secondaryControls: EngineWorkflowControl[];
  startWorkflowDisabledReason: string | null;
  workflowSummary: WorkflowSummaryCardData | null;
  primaryAction: EngineWorkflowControl;
};

export function EnginePageHeaderActions({
  isActionPending,
  onAction,
  primaryAction,
  primaryActionDisabled,
  secondaryControls,
  startWorkflowDisabledReason,
  workflowSummary,
}: Readonly<EnginePageHeaderActionsProps>) {
  return (
    <div className="flex flex-wrap gap-2">
      {workflowSummary ? (
        <>
          <StatusBadge status={workflowSummary.statusTone} label={workflowSummary.statusLabel} />
          <StatusBadge status={workflowSummary.modeTone} label={workflowSummary.modeLabel} />
        </>
      ) : null}
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
          className={
            control.tone === "danger" ? "ink-button-danger" : "ink-button-secondary"
          }
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
