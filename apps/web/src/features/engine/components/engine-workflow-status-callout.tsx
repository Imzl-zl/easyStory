"use client";

import type { WorkflowExecution } from "@/lib/api/types";

import { resolveWorkflowStatusCallout, type EngineTabKey } from "./engine-workflow-status-support";

type EngineWorkflowStatusCalloutProps = {
  workflow: WorkflowExecution | null | undefined;
  onOpenTab: (tab: EngineTabKey) => void;
};

export function EngineWorkflowStatusCallout({
  workflow,
  onOpenTab,
}: EngineWorkflowStatusCalloutProps) {
  const callout = resolveWorkflowStatusCallout(workflow);
  if (!callout) {
    return null;
  }

  const className =
    callout.tone === "danger"
      ? "bg-accent-danger/10 text-accent-danger"
      : "bg-accent-warning/10 text-accent-warning";

  return (
    <div className={`rounded-2xl px-4 py-4 ${className}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="text-sm font-medium">{callout.title}</p>
          <p className="text-sm leading-6">{callout.description}</p>
        </div>
        <button
          className="ink-button-secondary"
          onClick={() => onOpenTab(callout.targetTab)}
        >
          {callout.actionLabel}
        </button>
      </div>
    </div>
  );
}
