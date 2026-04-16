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
    <details className="rounded-3xl bg-muted shadow-sm p-4">
      <summary className="cursor-pointer list-none text-sm font-medium text-text-primary">
        查看原始 workflow 调试数据
      </summary>
      <p className="mt-3 text-sm leading-6 text-text-secondary">
        调试信息，包含完整的原始响应数据。
      </p>
      <div className="mt-4">
        <CodeBlock value={workflow} />
      </div>
    </details>
  );
}
