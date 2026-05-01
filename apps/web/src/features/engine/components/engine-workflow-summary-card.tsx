"use client";

import type { WorkflowSummaryCardData } from "./engine-workflow-summary-support";

type EngineWorkflowSummaryCardProps = {
  summary: WorkflowSummaryCardData;
};

export function EngineWorkflowSummaryCard({
  summary,
}: Readonly<EngineWorkflowSummaryCardProps>) {
  return (
    <div className="rounded p-4" style={{ background: "#1a1d23", border: "1px solid #2a2f35" }}>
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-medium" style={{ color: "#6b7280" }}>
            执行摘要
          </span>
          <span
            className="text-[10px] px-1.5 py-0.5 rounded"
            style={{
              background:
                summary.statusTone === "completed"
                  ? "rgba(34, 197, 94, 0.12)"
                  : summary.statusTone === "failed"
                    ? "rgba(220, 38, 38, 0.12)"
                    : summary.statusTone === "running"
                      ? "rgba(232, 184, 109, 0.12)"
                      : "#1f2328",
              color:
                summary.statusTone === "completed"
                  ? "#4ade80"
                  : summary.statusTone === "failed"
                    ? "#f87171"
                    : summary.statusTone === "running"
                      ? "#e8b86d"
                      : "#9ca3af",
            }}
          >
            {summary.statusLabel}
          </span>
        </div>
        <p className="text-[12px]" style={{ color: "#e8e6e3" }}>
          {summary.description}
        </p>
        <div className="grid grid-cols-2 gap-2">
          {summary.rows.map((row) => (
            <div
              key={row.label}
              className="rounded p-2.5"
              style={{ background: "#111418" }}
            >
              <p className="text-[10px] mb-0.5" style={{ color: "#4b5563" }}>
                {row.label}
              </p>
              <p className="text-[12px] font-medium" style={{ color: "#9ca3af" }}>
                {row.value}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
