"use client";

import { useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/ui/empty-state";
import type { ConfigRegistryDetail, ConfigRegistryType } from "@/lib/api/types";

import { ConfigRegistryStructuredEditor } from "./config-registry-structured-editor";
import type { ConfigRegistryEditorMode } from "./config-registry-state-support";
import { isConfigRegistryFormSupported } from "./config-registry-state-support";
import { formatConfigRegistryDocument, parseConfigRegistryDocument } from "./config-registry-support";

type ConfigRegistryEditorPanelProps = {
  detail: ConfigRegistryDetail | null;
  isPending: boolean;
  mode: ConfigRegistryEditorMode;
  onDirtyChange: (value: boolean) => void;
  onModeChange: (mode: ConfigRegistryEditorMode) => void;
  onSave: (payload: ConfigRegistryDetail) => void;
  type: ConfigRegistryType;
};

export function ConfigRegistryEditorPanel(props: Readonly<ConfigRegistryEditorPanelProps>) {
  if (!props.detail) {
    return <EmptyState title="暂无可编辑配置" description="选择配置后，可以编辑结构化表单或 JSON。" />;
  }
  return <ConfigRegistryEditorPanelBody key={formatConfigRegistryDocument(props.detail)} {...props} detail={props.detail} />;
}

function ConfigRegistryEditorPanelBody({
  detail,
  isPending,
  mode,
  onDirtyChange,
  onModeChange,
  onSave,
  type,
}: Readonly<ConfigRegistryEditorPanelProps & { detail: ConfigRegistryDetail }>) {
  const [jsonValue, setJsonValue] = useState(() => formatConfigRegistryDocument(detail));
  const [structuredDraft, setStructuredDraft] = useState<ConfigRegistryDetail>(detail);
  const supportsForm = isConfigRegistryFormSupported(type);
  const parsedJson = useMemo(() => parseConfigRegistryDocument(jsonValue), [jsonValue]);
  const jsonDirty = jsonValue !== formatConfigRegistryDocument(detail);
  const canSwitchToForm = supportsForm && parsedJson.parsed !== null;

  useEffect(() => {
    if (mode === "json") {
      onDirtyChange(jsonDirty);
    }
  }, [jsonDirty, mode, onDirtyChange]);

  return (
    <div className="space-y-4">
      <section className="panel-muted space-y-4 p-5">
        <header className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="space-y-1">
              <p className="text-xs uppercase tracking-[0.18em] text-[var(--accent-ink)]">编辑器</p>
              <h3 className="font-serif text-lg font-semibold">{getEditorTitle(type)}</h3>
            </div>
            {supportsForm ? (
              <div className="flex flex-wrap gap-2">
                <ModeButton
                  isActive={mode === "form"}
                  label="表单视图"
                  onClick={() => {
                    if (!canSwitchToForm) return;
                    setStructuredDraft(parsedJson.parsed as ConfigRegistryDetail);
                    onModeChange("form");
                  }}
                />
                <ModeButton
                  isActive={mode === "json"}
                  label="JSON 高级模式"
                  onClick={() => {
                    setJsonValue(formatConfigRegistryDocument(structuredDraft));
                    onModeChange("json");
                  }}
                />
              </div>
            ) : (
              <div className="rounded-full bg-[rgba(46,111,106,0.08)] px-3 py-2 text-sm text-[var(--accent-ink)]">
                Workflow 当前仅支持 JSON 模式
              </div>
            )}
          </div>
          <p className="text-sm leading-6 text-[var(--text-secondary)]">
            {mode === "json"
              ? "JSON 模式直接提交完整 DTO。保存前会先做前端解析，严格字段校验继续以后端 422 为准。"
              : "表单模式按类型展开常用字段；复杂对象仍以当前 DTO 结构为真值。"}
          </p>
        </header>

        {mode === "json" ? (
          <JsonEditor
            errorMessage={parsedJson.errorMessage}
            isDirty={jsonDirty}
            isPending={isPending}
            value={jsonValue}
            onChange={setJsonValue}
            onReset={() => setJsonValue(formatConfigRegistryDocument(detail))}
            onSave={() => {
              if (parsedJson.parsed) onSave(parsedJson.parsed as ConfigRegistryDetail);
            }}
          />
        ) : (
          <ConfigRegistryStructuredEditor
            detail={structuredDraft}
            isPending={isPending}
            type={type}
            onDraftChange={setStructuredDraft}
            onDirtyChange={onDirtyChange}
            onSave={onSave}
          />
        )}
      </section>
    </div>
  );
}

function JsonEditor({
  errorMessage,
  isDirty,
  isPending,
  onChange,
  onReset,
  onSave,
  value,
}: Readonly<{
  errorMessage: string | null;
  isDirty: boolean;
  isPending: boolean;
  onChange: (value: string) => void;
  onReset: () => void;
  onSave: () => void;
  value: string;
}>) {
  return (
    <div className="space-y-4">
      {errorMessage ? <ErrorBanner message={errorMessage} /> : null}
      <textarea
        autoComplete="off"
        className="ink-textarea min-h-[540px] font-mono text-sm"
        spellCheck={false}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
      <div className="flex flex-wrap gap-2">
        <button className="ink-button" disabled={isPending || !isDirty || Boolean(errorMessage)} type="button" onClick={onSave}>
          {isPending ? "保存中…" : "保存配置"}
        </button>
        <button className="ink-button-secondary" disabled={isPending || !isDirty} type="button" onClick={onReset}>
          还原编辑
        </button>
      </div>
    </div>
  );
}

function ModeButton({
  isActive,
  label,
  onClick,
}: Readonly<{ isActive: boolean; label: string; onClick: () => void }>) {
  return (
    <button className="ink-tab" data-active={isActive} type="button" onClick={onClick}>
      {label}
    </button>
  );
}

function ErrorBanner({ message }: Readonly<{ message: string }>) {
  return (
    <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
      {message}
    </div>
  );
}

function getEditorTitle(type: ConfigRegistryType): string {
  if (type === "skills") return "Skill 配置编辑";
  if (type === "agents") return "Agent 配置编辑";
  if (type === "hooks") return "Hook 配置编辑";
  if (type === "mcp_servers") return "MCP Server 配置编辑";
  return "Workflow 配置编辑";
}
