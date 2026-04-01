"use client";

import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import { JsonTextAreaField } from "@/features/config-registry/components/config-registry-json-field";
import type { AssistantMcpDetail } from "@/lib/api/types";

import {
  AssistantDocumentModeToggle,
  type AssistantDocumentEditMode,
} from "./assistant-document-mode-toggle";
import { AssistantMcpRawEditor } from "./assistant-mcp-raw-editor";
import {
  ASSISTANT_MCP_FILE_LABEL,
  buildAssistantMcpDocumentPreview,
  createEmptyAssistantMcpDraft,
  isAssistantMcpDirty,
  parseAssistantMcpDocument,
  sanitizeAssistantMcpTimeoutInput,
  toAssistantMcpDraft,
  type AssistantMcpDraft,
  validateAssistantMcpHeaders,
} from "./assistant-mcp-support";

type AssistantMcpEditorProps = {
  detail: AssistantMcpDetail | null;
  isPending: boolean;
  mode: "create" | "edit";
  onDelete?: () => void;
  onDirtyChange?: (isDirty: boolean) => void;
  onSubmit: (draft: AssistantMcpDraft) => void;
};

export function AssistantMcpEditor({
  detail,
  isPending,
  mode,
  onDelete,
  onDirtyChange,
  onSubmit,
}: AssistantMcpEditorProps) {
  const [draft, setDraft] = useState<AssistantMcpDraft>(() => buildInitialDraft(detail));
  const [editorMode, setEditorMode] = useState<AssistantDocumentEditMode>("guided");
  const [documentValue, setDocumentValue] = useState(() =>
    buildAssistantMcpDocumentPreview(buildInitialDraft(detail), { serverId: detail?.id ?? null }),
  );
  const [documentError, setDocumentError] = useState<string | null>(null);
  const [headersError, setHeadersError] = useState<string | null>(null);
  const hasFieldError = useMemo(
    () => editorMode === "guided" && Boolean(headersError),
    [editorMode, headersError],
  );
  const isDirty = hasFieldError || Boolean(documentError) || isAssistantMcpDirty(draft, detail);

  useEffect(() => {
    onDirtyChange?.(isDirty);
    return () => onDirtyChange?.(false);
  }, [isDirty, onDirtyChange]);

  return (
    <form className="panel-muted space-y-10 p-10" onSubmit={(event) => submitDraft(event, draft, onSubmit)}>
      <AssistantDocumentModeToggle
        description="可以继续用可视化方式维护连接，也可以直接按 MCP.yaml 来写。"
        fileLabel={ASSISTANT_MCP_FILE_LABEL}
        guidedDisabled={Boolean(documentError)}
        mode={editorMode}
        onChange={setEditorMode}
      />
      {editorMode === "guided" ? (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.92fr)]">
          <div className="space-y-4">
            <div className="rounded-2xl bg-[rgba(248,243,235,0.92)] px-4 py-3 text-xs leading-6 text-[var(--text-secondary)]">
              MCP 用来保存你自己的外部工具连接。创建好以后，就可以在 Hooks 里直接选它来执行。
            </div>
            <TextField label="名称" maxLength={80} placeholder="例如：资料检索" value={draft.name} onChange={(value) => applyDraft({ ...draft, name: value }, detail?.id ?? null, setDraft, setDocumentValue, setDocumentError)} />
            <TextareaField label="一句说明" maxLength={240} placeholder="例如：给 Hook 调用的资料查询工具。" value={draft.description} onChange={(value) => applyDraft({ ...draft, description: value }, detail?.id ?? null, setDraft, setDocumentValue, setDocumentError)} />
            <ToggleField checked={draft.enabled} description="停用后会保留这条连接，但聊天里的 Hook 暂时不会执行它。" label="启用" onChange={(checked) => applyDraft({ ...draft, enabled: checked }, detail?.id ?? null, setDraft, setDocumentValue, setDocumentError)} />
            <TextField label="地址" maxLength={2000} placeholder="https://example.com/mcp" value={draft.url} onChange={(value) => applyDraft({ ...draft, url: value }, detail?.id ?? null, setDraft, setDocumentValue, setDocumentError)} />
            <TextField label="超时（秒）" maxLength={4} placeholder="30" value={draft.timeout} onChange={(value) => applyDraft({ ...draft, timeout: sanitizeAssistantMcpTimeoutInput(value) }, detail?.id ?? null, setDraft, setDocumentValue, setDocumentError)} />
            <JsonTextAreaField emptyValue={{}} helpText='例如：{ "Authorization": "Bearer ..." }' label="请求头" parseValue={validateAssistantMcpHeaders} value={draft.headers} onChange={(value) => applyDraft({ ...draft, headers: value ?? {} }, detail?.id ?? null, setDraft, setDocumentValue, setDocumentError)} onErrorChange={setHeadersError} />
          </div>
          <div className="space-y-3">
            <PreviewCard fileLabel={ASSISTANT_MCP_FILE_LABEL} preview={documentValue} />
            <div className="rounded-[24px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.72)] px-4 py-3">
              <p className="text-sm font-medium text-[var(--text-primary)]">当前效果</p>
              <p className="mt-1 text-[12px] leading-5 text-[var(--text-secondary)]">这个 MCP 会通过 `streamable_http` 方式连接，保存后可以在 Hooks 里直接选用。</p>
            </div>
          </div>
        </div>
      ) : (
        <AssistantMcpRawEditor
          documentError={documentError}
          documentValue={documentValue}
          mode={mode}
          onChange={(value) => applyDocument(value, detail?.id ?? null, setDraft, setDocumentValue, setDocumentError)}
        />
      )}
      <div className="flex flex-wrap items-center justify-end gap-2">
        {hasFieldError || documentError ? (
          <p className="mr-auto rounded-2xl bg-[rgba(178,65,46,0.08)] px-3 py-2 text-[12px] leading-5 text-[var(--accent-danger)]">
            {documentError ?? "请先修正请求头格式，再保存。"}
          </p>
        ) : null}
        <button className="ink-button" disabled={isPending || !isDirty || hasFieldError || Boolean(documentError)} type="submit">
          {isPending ? "保存中..." : mode === "create" ? "创建 MCP" : "保存修改"}
        </button>
        <button className="ink-button-secondary" disabled={isPending || !isDirty} type="button" onClick={() => { const nextDraft = buildInitialDraft(detail); setDraft(nextDraft); setDocumentValue(buildAssistantMcpDocumentPreview(nextDraft, { serverId: detail?.id ?? null })); setDocumentError(null); setHeadersError(null); }}>
          还原
        </button>
        {mode === "edit" && detail && onDelete ? (
          <button className="ink-button-secondary" disabled={isPending} type="button" onClick={onDelete}>
            删除
          </button>
        ) : null}
      </div>
    </form>
  );
}

function PreviewCard({
  fileLabel,
  preview,
}: Readonly<{
  fileLabel: string;
  preview: string;
}>) {
  return (
    <div className="rounded-[24px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.72)] p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-[var(--text-primary)]">保存后的文件</p>
          <p className="mt-1 text-[12px] leading-5 text-[var(--text-secondary)]">右侧会同步预览这条 MCP 最终保存成什么样。</p>
        </div>
        <span className="rounded-full bg-[rgba(248,243,235,0.92)] px-3 py-1 text-[12px] font-medium text-[var(--text-secondary)]">{fileLabel}</span>
      </div>
      <pre className="mt-3 max-h-[320px] overflow-auto rounded-[18px] bg-[rgba(248,243,235,0.84)] px-4 py-4 text-[12px] leading-6 text-[var(--text-primary)]">{preview}</pre>
    </div>
  );
}

function TextField({
  label,
  maxLength,
  placeholder,
  value,
  onChange,
}: Readonly<{
  label: string;
  maxLength: number;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
}>) {
  return <label className="block space-y-2"><span className="text-sm font-medium text-[var(--text-primary)]">{label}</span><input className="ink-input" maxLength={maxLength} placeholder={placeholder} value={value} onChange={(event) => onChange(event.target.value)} /></label>;
}

function TextareaField({
  label,
  maxLength,
  placeholder,
  value,
  onChange,
}: Readonly<{
  label: string;
  maxLength: number;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
}>) {
  return <label className="block space-y-2"><span className="text-sm font-medium text-[var(--text-primary)]">{label}</span><textarea className="ink-input min-h-[88px]" maxLength={maxLength} placeholder={placeholder} value={value} onChange={(event) => onChange(event.target.value)} /></label>;
}

function ToggleField({
  checked,
  description,
  label,
  onChange,
}: Readonly<{
  checked: boolean;
  description: string;
  label: string;
  onChange: (value: boolean) => void;
}>) {
  return <label className="flex items-start gap-3 rounded-2xl border border-[var(--line-soft)] bg-[rgba(255,255,255,0.7)] px-4 py-3"><input checked={checked} className="mt-1 size-4 shrink-0 accent-[var(--accent-ink)]" type="checkbox" onChange={(event) => onChange(event.target.checked)} /><span className="space-y-1"><span className="block text-sm font-medium text-[var(--text-primary)]">{label}</span><span className="block text-[12px] leading-5 text-[var(--text-secondary)]">{description}</span></span></label>;
}

function buildInitialDraft(detail: AssistantMcpDetail | null) {
  return detail ? toAssistantMcpDraft(detail) : createEmptyAssistantMcpDraft();
}

function applyDraft(
  draft: AssistantMcpDraft,
  serverId: string | null,
  setDraft: (draft: AssistantMcpDraft) => void,
  setDocumentValue: (value: string) => void,
  setDocumentError: (value: string | null) => void,
) {
  setDraft(draft);
  setDocumentValue(buildAssistantMcpDocumentPreview(draft, { serverId }));
  setDocumentError(null);
}

function applyDocument(
  value: string,
  serverId: string | null,
  setDraft: (draft: AssistantMcpDraft) => void,
  setDocumentValue: (value: string) => void,
  setDocumentError: (value: string | null) => void,
) {
  setDocumentValue(value);
  try {
    setDraft(parseAssistantMcpDocument(value, serverId));
    setDocumentError(null);
  } catch (error) {
    setDocumentError(error instanceof Error ? error.message : "MCP.yaml 解析失败。");
  }
}

function submitDraft(
  event: FormEvent<HTMLFormElement>,
  draft: AssistantMcpDraft,
  onSubmit: (draft: AssistantMcpDraft) => void,
) {
  event.preventDefault();
  onSubmit(draft);
}
