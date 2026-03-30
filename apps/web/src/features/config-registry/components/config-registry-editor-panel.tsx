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
    return <EmptyState title="选择配置项" description="从左侧选择后即可编辑。" />;
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
              <p className="text-xs tracking-[0.16em] text-[var(--accent-ink)]">当前编辑</p>
              <h3 className="font-serif text-lg font-semibold">{getEditorTitle(type)}</h3>
            </div>
            {supportsForm ? (
              <div className="flex flex-wrap items-center gap-2.5">
                <ModeButton
                  isActive={mode === "form"}
                  label={getFormModeLabel(type)}
                  onClick={() => {
                    if (!canSwitchToForm) return;
                    setStructuredDraft(parsedJson.parsed as ConfigRegistryDetail);
                    onModeChange("form");
                  }}
                />
                <ModeButton
                  isActive={mode === "json"}
                  label={getJsonModeLabel(type)}
                  onClick={() => {
                    setJsonValue(formatConfigRegistryDocument(structuredDraft));
                    onModeChange("json");
                  }}
                />
              </div>
            ) : (
              <div className="rounded-full bg-[rgba(46,111,106,0.08)] px-3 py-2 text-sm text-[var(--accent-ink)]">
                Workflows 当前仅支持原始配置
              </div>
            )}
          </div>
          <p className="text-sm leading-6 text-[var(--text-secondary)]">
            {getEditorDescription(type, mode)}
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
      <div className="flex flex-wrap items-center gap-2.5 pt-1">
        <button className="ink-button h-9 px-4 text-[13px]" disabled={isPending || !isDirty || Boolean(errorMessage)} type="button" onClick={onSave}>
          {isPending ? "保存中…" : "保存修改"}
        </button>
        <button className="ink-button-secondary h-9 px-4 text-[13px]" disabled={isPending || !isDirty} type="button" onClick={onReset}>
          撤销修改
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
    <button className="ink-tab h-9 px-4 text-[13px]" data-active={isActive} type="button" onClick={onClick}>
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
  if (type === "skills") return "Skill 编辑";
  if (type === "agents") return "Agents";
  if (type === "hooks") return "Hooks";
  if (type === "mcp_servers") return "MCP";
  return "Workflows";
}

function getEditorDescription(type: ConfigRegistryType, mode: ConfigRegistryEditorMode): string {
  if (type === "skills") {
    return mode === "json"
      ? "这里显示 Skill 的原始配置，通常只在核对字段或排查问题时使用。"
      : "在这里修改名称、提示词、字段结构和模型设置。";
  }
  return mode === "json" ? "编辑完整配置。" : "编辑常用字段。";
}

function getFormModeLabel(type: ConfigRegistryType): string {
  return type === "skills" ? "字段编辑" : "常用字段";
}

function getJsonModeLabel(type: ConfigRegistryType): string {
  return type === "skills" ? "原始配置" : "完整配置";
}
