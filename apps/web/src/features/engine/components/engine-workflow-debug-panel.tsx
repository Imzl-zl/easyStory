"use client";

import { CodeBlock } from "@/components/ui/code-block";
import type { WorkflowExecution } from "@/lib/api/types";

type EngineWorkflowDebugPanelProps = {
  workflow: WorkflowExecution;
};

export function EngineWorkflowDebugPanel({
  workflow,
}: Readonly<EngineWorkflowDebugPanelProps>) {
  return (
    <details className="rounded" style={{ background: "var(--bg-muted)", border: "1px solid var(--line-soft)" }}>
      <summary
        className="cursor-pointer list-none px-4 py-3 text-[11px] font-medium flex items-center justify-between"
        style={{ color: "var(--text-tertiary)" }}
      >
        <span>调试数据</span>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </summary>
      <div className="px-4 pb-4">
        <CodeBlock value={workflow} />
      </div>
    </details>
  );
}
