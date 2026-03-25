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
    <details className="rounded-[24px] border border-[rgba(101,92,82,0.12)] bg-[rgba(255,255,255,0.52)] p-4">
      <summary className="cursor-pointer list-none text-sm font-medium text-[var(--text-primary)]">
        查看原始 workflow 调试数据
      </summary>
      <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">
        这里保留后端原始响应，供排查字段和值是否一致使用，不再占主信息层。
      </p>
      <div className="mt-4">
        <CodeBlock value={workflow} />
      </div>
    </details>
  );
}
