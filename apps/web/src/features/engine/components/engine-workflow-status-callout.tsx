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

  return (
    <div
      className="rounded p-4"
      style={{
        background: callout.tone === "danger" ? "var(--accent-danger-soft)" : "var(--accent-warning-soft)",
        border: `1px solid ${callout.tone === "danger" ? "var(--accent-danger-muted)" : "var(--accent-warning-muted)"}`,
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1 min-w-0">
          <p className="text-[12px] font-medium" style={{ color: callout.tone === "danger" ? "var(--accent-danger)" : "var(--accent-warning)" }}>
            {callout.title}
          </p>
          <p className="text-[11px] leading-relaxed" style={{ color: "var(--text-secondary)" }}>
            {callout.description}
          </p>
        </div>
        <button
          className="flex-shrink-0 px-3 py-1.5 rounded text-[11px] font-medium transition-colors"
          style={{
            background: callout.tone === "danger" ? "var(--accent-danger-soft)" : "var(--accent-warning-soft)",
            color: callout.tone === "danger" ? "var(--accent-danger)" : "var(--accent-warning)",
          }}
          onClick={() => onOpenTab(callout.targetTab)}
        >
          {callout.actionLabel}
        </button>
      </div>
    </div>
  );
}
