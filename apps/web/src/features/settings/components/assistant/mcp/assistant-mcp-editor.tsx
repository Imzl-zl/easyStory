"use client";

import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import { JsonTextAreaField } from "@/features/config-registry/components/config-registry-json-field";
import type { AssistantMcpDetail } from "@/lib/api/types";

import {
  AssistantDocumentModeToggle,
  type AssistantDocumentEditMode,
} from "@/features/settings/components/assistant/common/assistant-document-mode-toggle";
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
} from "@/features/settings/components/assistant/mcp/assistant-mcp-support";

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
    <form
      className="px-5 py-4 space-y-5"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(draft);
      }}
    >
      <AssistantDocumentModeToggle
        fileLabel={ASSISTANT_MCP_FILE_LABEL}
        guidedDisabled={Boolean(documentError)}
        mode={editorMode}
        onChange={setEditorMode}
      />

      {editorMode === "guided" ? (
        <GuidedMcpEditor
          draft={draft}
          serverId={detail?.id ?? null}
          onChange={(nextDraft) => applyDraft(nextDraft, detail?.id ?? null, setDraft, setDocumentValue, setDocumentError)}
          onHeadersErrorChange={setHeadersError}
        />
      ) : (
        <RawMcpEditor
          documentError={documentError}
          documentValue={documentValue}
          mode={mode}
          onChange={(value) => applyDocument(value, detail?.id ?? null, setDraft, setDocumentValue, setDocumentError)}
        />
      )}

      {/* Actions */}
      <div className="flex gap-2 pt-1">
        {hasFieldError || documentError ? (
          <p className="mr-auto rounded-md px-3 py-2 text-[12px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
            {documentError ?? "请先修正请求头格式，再保存。"}
          </p>
        ) : null}
        <button
          className="h-8 px-4 rounded-md text-[12px] font-medium transition-colors"
          disabled={isPending || !isDirty || hasFieldError || Boolean(documentError)}
          style={{
            background: isDirty && !hasFieldError && !documentError ? "var(--accent-primary)" : "var(--line-soft)",
            color: isDirty && !hasFieldError && !documentError ? "var(--text-on-accent)" : "var(--text-tertiary)",
          }}
          type="submit"
        >
          {isPending ? "保存中..." : mode === "create" ? "创建 MCP" : "保存修改"}
        </button>
        <button
          className="h-8 px-4 rounded-md text-[12px] font-medium"
          disabled={isPending || !isDirty}
          onClick={() => {
            const nextDraft = buildInitialDraft(detail);
            setDraft(nextDraft);
            setDocumentValue(buildAssistantMcpDocumentPreview(nextDraft, { serverId: detail?.id ?? null }));
            setDocumentError(null);
            setHeadersError(null);
          }}
          style={{ background: "var(--line-soft)", color: "var(--text-secondary)", border: "1px solid var(--line-medium)" }}
          type="button"
        >
          还原
        </button>
        {mode === "edit" && detail && onDelete ? (
          <button
            className="h-8 px-4 rounded-md text-[12px] font-medium"
            disabled={isPending}
            style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}
            type="button"
            onClick={onDelete}
          >
            删除
          </button>
        ) : null}
      </div>
    </form>
  );
}

function buildInitialDraft(detail: AssistantMcpDetail | null) {
  return detail ? toAssistantMcpDraft(detail) : createEmptyAssistantMcpDraft();
}

function GuidedMcpEditor({
  draft,
  serverId,
  onChange,
  onHeadersErrorChange,
}: Readonly<{
  draft: AssistantMcpDraft;
  serverId: string | null;
  onChange: (draft: AssistantMcpDraft) => void;
  onHeadersErrorChange: (message: string | null) => void;
}>) {
  return (
    <div className="space-y-4">
      {/* Info Banner */}
      <div className="rounded-md px-3 py-2 text-[11px]" style={{ background: "var(--accent-primary-soft)", color: "var(--accent-primary)", border: "1px solid var(--accent-primary-soft)" }}>
        MCP 用来保存你自己的外部工具连接。创建好以后，就可以在 Hooks 里直接选它来执行。
      </div>

      {/* Basic Info */}
      <div className="grid gap-3 sm:grid-cols-2">
        <FormField label="名称">
          <input
            className="w-full h-8 px-3 rounded-md text-[12px]"
            style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-medium)" }}
            maxLength={80}
            placeholder="例如：资料检索"
            value={draft.name}
            onChange={(event) => onChange({ ...draft, name: event.target.value })}
          />
        </FormField>

        <FormField label="启用状态">
          <label className="flex items-center gap-2 h-8 px-3 rounded-md cursor-pointer" style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-medium)" }}>
            <input
              checked={draft.enabled}
              className="size-3.5 accent-[var(--accent-primary)]"
              type="checkbox"
              onChange={(event) => onChange({ ...draft, enabled: event.target.checked })}
            />
            <span className="text-[12px]" style={{ color: "var(--text-primary)" }}>{draft.enabled ? "已启用" : "已停用"}</span>
          </label>
        </FormField>
      </div>

      <FormField label="一句说明">
        <textarea
          className="w-full px-3 py-2 rounded-md text-[12px] resize-y"
          style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-medium)", minHeight: "64px" }}
          maxLength={240}
          placeholder="例如：给 Hook 调用的资料查询工具。"
          value={draft.description}
          onChange={(event) => onChange({ ...draft, description: event.target.value })}
        />
      </FormField>

      {/* Connection Info */}
      <div className="grid gap-3 sm:grid-cols-2">
        <FormField label="地址">
          <input
            className="w-full h-8 px-3 rounded-md text-[12px]"
            style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-medium)" }}
            maxLength={2000}
            placeholder="https://example.com/mcp"
            value={draft.url}
            onChange={(event) => onChange({ ...draft, url: event.target.value })}
          />
        </FormField>

        <FormField label="超时（秒）">
          <input
            className="w-full h-8 px-3 rounded-md text-[12px]"
            style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-medium)" }}
            inputMode="numeric"
            maxLength={4}
            placeholder="30"
            value={draft.timeout}
            onChange={(event) => onChange({ ...draft, timeout: sanitizeAssistantMcpTimeoutInput(event.target.value) })}
          />
        </FormField>
      </div>

      <JsonTextAreaField
        emptyValue={{}}
        helpText='例如：{ "Authorization": "Bearer ..." }'
        label="请求头"
        parseValue={validateAssistantMcpHeaders}
        value={draft.headers}
        onChange={(value) => onChange({ ...draft, headers: value ?? {} })}
        onErrorChange={onHeadersErrorChange}
      />

      {/* Preview */}
      <div
        className="rounded-md p-3"
        style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}
      >
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-medium" style={{ color: "var(--text-secondary)" }}>保存后的文件</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: "var(--line-soft)", color: "var(--text-tertiary)" }}>{ASSISTANT_MCP_FILE_LABEL}</span>
        </div>
        <pre
          className="text-[11px] leading-4 overflow-auto rounded px-2 py-2"
          style={{ background: "var(--bg-canvas)", color: "var(--text-secondary)", maxHeight: "160px" }}
        >
          {buildAssistantMcpDocumentPreview(draft, { serverId })}
        </pre>
      </div>
    </div>
  );
}

function RawMcpEditor({
  documentError,
  documentValue,
  mode,
  onChange,
}: Readonly<{
  documentError: string | null;
  documentValue: string;
  mode: "create" | "edit";
  onChange: (value: string) => void;
}>) {
  return (
    <div className="space-y-4">
      <FormField label="MCP.yaml">
        <textarea
          className="w-full px-3 py-2 rounded-md text-[12px] resize-y font-mono"
          style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-medium)", minHeight: "320px" }}
          spellCheck={false}
          value={documentValue}
          onChange={(event) => onChange(event.target.value)}
        />
        <p className="text-[10px] mt-1" style={{ color: "var(--text-tertiary)" }}>按约定直接写，保存后立即生效</p>
      </FormField>

      <div
        className="rounded-md p-3"
        style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}
      >
        <p className="text-[11px] font-medium mb-2" style={{ color: "var(--text-secondary)" }}>文件约定</p>
        <p className="text-[11px] leading-4" style={{ color: "var(--text-tertiary)" }}>
          支持标准 YAML frontmatter。name、enabled、url、transport、timeout 都能直接写。
        </p>
        {mode === "create" ? (
          <p className="mt-2 text-[11px]" style={{ color: "var(--accent-warning)" }}>
            第一次保存后，系统会自动补上这份 MCP 的 id。
          </p>
        ) : null}
        {documentError ? (
          <p className="mt-2 rounded-md px-3 py-2 text-[11px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
            {documentError}
          </p>
        ) : null}
      </div>
    </div>
  );
}

function FormField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-[11px] font-medium" style={{ color: "var(--text-secondary)" }}>{label}</label>
      {children}
    </div>
  );
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
