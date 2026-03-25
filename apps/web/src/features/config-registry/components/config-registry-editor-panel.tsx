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
            编辑区直接提交完整 JSON DTO。保存前会先做前端 JSON 解析，字段校验继续以后端 422 为准。
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
    return "Skill 配置编辑";
  }
  if (type === "agents") {
    return "Agent 配置编辑";
  }
  if (type === "hooks") {
    return "Hook 配置编辑";
  }
  return "Workflow 配置编辑";
}
