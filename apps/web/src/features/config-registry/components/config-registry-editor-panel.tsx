"use client";

import { EmptyState } from "@/components/ui/empty-state";
import type { ConfigRegistryType } from "@/lib/api/types";

type ConfigRegistryEditorPanelProps = {
  detailId: string | null;
  editorValue: string;
  errorMessage: string | null;
  isDirty: boolean;
  isPending: boolean;
  onChange: (value: string) => void;
  onReset: () => void;
  onSave: () => void;
  type: ConfigRegistryType;
};

export function ConfigRegistryEditorPanel({
  detailId,
  editorValue,
  errorMessage,
  isDirty,
  isPending,
  onChange,
  onReset,
  onSave,
  type,
}: Readonly<ConfigRegistryEditorPanelProps>) {
  if (!detailId) {
    return (
      <EmptyState
        title="暂无可编辑配置"
        description="选择配置后，可以编辑 JSON 内容。"
      />
    );
  }

  return (
    <div className="space-y-4">
      <section className="panel-muted space-y-4 p-5">
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-[0.18em] text-[var(--accent-ink)]">
            编辑器
          </p>
          <h3 className="font-serif text-lg font-semibold">{getEditorTitle(type)}</h3>
          <p className="text-sm leading-6 text-[var(--text-secondary)]">
            直接编辑 JSON 格式的配置内容。保存时会校验格式是否正确。
          </p>
        </div>
        {errorMessage ? (
          <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
            {errorMessage}
          </div>
        ) : null}
        <textarea
          className="ink-textarea min-h-[540px] font-mono text-sm"
          spellCheck={false}
          value={editorValue}
          onChange={(event) => onChange(event.target.value)}
        />
        <div className="flex flex-wrap gap-2">
          <button
            className="ink-button"
            disabled={isPending || !isDirty || Boolean(errorMessage)}
            onClick={onSave}
            type="button"
          >
            {isPending ? "保存中..." : "保存配置"}
          </button>
          <button
            className="ink-button-secondary"
            disabled={isPending || !isDirty}
            onClick={onReset}
            type="button"
          >
            还原编辑
          </button>
        </div>
      </section>
    </div>
  );
}

function getEditorTitle(type: ConfigRegistryType): string {
  if (type === "skills") {
    return "Skill 配置";
  }
  if (type === "agents") {
    return "Agent 配置";
  }
  if (type === "hooks") {
    return "Hook 配置";
  }
  if (type === "mcp_servers") {
    return "MCP Server 配置";
  }
  return "Workflow 配置";
}
