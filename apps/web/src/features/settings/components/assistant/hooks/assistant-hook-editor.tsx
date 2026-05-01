"use client";

import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import type { AssistantHookDetail } from "@/lib/api/types";

import { JsonTextAreaField } from "@/features/config-registry/components/config-registry-json-field";
import {
  AssistantDocumentModeToggle,
  type AssistantDocumentEditMode,
} from "@/features/settings/components/assistant/common/assistant-document-mode-toggle";
import {
  ASSISTANT_HOOK_ACTION_TYPE_OPTIONS,
  ASSISTANT_HOOK_EVENT_OPTIONS,
  ASSISTANT_HOOK_FILE_LABEL,
  buildAssistantHookDocumentPreview,
  createEmptyAssistantHookDraft,
  isAssistantHookDirty,
  parseAssistantHookDocument,
  toAssistantHookDraft,
  validateAssistantHookJsonObject,
  validateAssistantHookStringMap,
  type AssistantHookDraft,
} from "@/features/settings/components/assistant/hooks/assistant-hooks-support";

type AssistantHookEditorProps = {
  agentErrorMessage?: string | null;
  agentOptions?: { label: string; value: string; description?: string }[];
  detail: AssistantHookDetail | null;
  isPending: boolean;
  mcpErrorMessage?: string | null;
  mcpOptions?: { label: string; value: string; description?: string }[];
  mode: "create" | "edit";
  onDelete?: () => void;
  onDirtyChange?: (isDirty: boolean) => void;
  onSubmit: (draft: AssistantHookDraft) => void;
};

export function AssistantHookEditor({
  agentErrorMessage,
  agentOptions,
  detail,
  isPending,
  mcpErrorMessage,
  mcpOptions,
  mode,
  onDelete,
  onDirtyChange,
  onSubmit,
}: AssistantHookEditorProps) {
  const [draft, setDraft] = useState<AssistantHookDraft>(() => buildInitialDraft(detail));
  const [editorMode, setEditorMode] = useState<AssistantDocumentEditMode>("guided");
  const [documentValue, setDocumentValue] = useState(() =>
    buildAssistantHookDocumentPreview(buildInitialDraft(detail), { hookId: detail?.id ?? null }),
  );
  const [documentError, setDocumentError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<"agentInputMapping" | "arguments" | "inputMapping", string | null>>>({});
  const hasFieldError = useMemo(
    () => editorMode === "guided" && Object.values(fieldErrors).some(Boolean),
    [editorMode, fieldErrors],
  );
  const isDirty = hasFieldError || Boolean(documentError) || isAssistantHookDirty(draft, detail);

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
        fileLabel={ASSISTANT_HOOK_FILE_LABEL}
        guidedDisabled={Boolean(documentError)}
        mode={editorMode}
        onChange={setEditorMode}
      />

      {editorMode === "guided" ? (
        <GuidedHookEditor
          agentErrorMessage={agentErrorMessage}
          agentOptions={agentOptions}
          draft={draft}
          mcpErrorMessage={mcpErrorMessage}
          mcpOptions={mcpOptions}
          onChange={(nextDraft) => applyDraft(nextDraft, detail?.id ?? null, setDraft, setDocumentValue, setDocumentError)}
          onFieldErrorChange={(field, message) => setFieldErrors((current) => ({ ...current, [field]: message }))}
        />
      ) : (
        <RawHookEditor
          agentErrorMessage={agentErrorMessage}
          agentOptions={agentOptions}
          documentError={documentError}
          documentValue={documentValue}
          mode={mode}
          mcpErrorMessage={mcpErrorMessage}
          mcpOptions={mcpOptions}
          onChange={(value) => applyDocument(value, detail?.id ?? null, setDraft, setDocumentValue, setDocumentError)}
        />
      )}

      {/* Actions */}
      <div className="flex gap-2 pt-1">
        {hasFieldError || documentError ? (
          <p className="mr-auto rounded-md px-3 py-2 text-[12px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
            {documentError ?? "请先修正上面的格式问题，再保存。"}
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
          {isPending ? "保存中..." : mode === "create" ? "创建 Hook" : "保存修改"}
        </button>
        <button
          className="h-8 px-4 rounded-md text-[12px] font-medium"
          disabled={isPending || !isDirty}
          onClick={() => {
            const nextDraft = buildInitialDraft(detail);
            setDraft(nextDraft);
            setDocumentValue(buildAssistantHookDocumentPreview(nextDraft, { hookId: detail?.id ?? null }));
            setDocumentError(null);
            setFieldErrors({});
          }}
          style={{ background: "var(--bg-surface)", color: "var(--text-secondary)", border: "1px solid var(--line-medium)" }}
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

function buildInitialDraft(detail: AssistantHookDetail | null) {
  return detail ? toAssistantHookDraft(detail) : createEmptyAssistantHookDraft();
}

function GuidedHookEditor({
  agentErrorMessage,
  agentOptions,
  draft,
  mcpErrorMessage,
  mcpOptions,
  onChange,
  onFieldErrorChange,
}: Readonly<{
  agentErrorMessage?: string | null;
  agentOptions?: { label: string; value: string; description?: string }[];
  draft: AssistantHookDraft;
  mcpErrorMessage?: string | null;
  mcpOptions?: { label: string; value: string; description?: string }[];
  onChange: (draft: AssistantHookDraft) => void;
  onFieldErrorChange: (field: "agentInputMapping" | "arguments" | "inputMapping", message: string | null) => void;
}>) {
  return (
    <div className="space-y-4">
      {/* Info Banner */}
      <div className="rounded-md px-3 py-2 text-[11px]" style={{ background: "var(--accent-primary-soft)", color: "var(--accent-primary)", border: "1px solid var(--accent-primary-soft)" }}>
        Hook 会在回复前后自动多做一步。你可以让它调用一个 Agent，也可以直接连接一个 MCP 工具。
      </div>

      {/* Basic Info */}
      <div className="grid gap-3 sm:grid-cols-2">
        <FormField label="名称">
          <input
            className="w-full h-8 px-3 rounded-md text-[12px]"
            style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-medium)" }}
            maxLength={80}
            placeholder="例如：回复后自动整理"
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
          placeholder="例如：每次回复后自动提炼一句重点。"
          value={draft.description}
          onChange={(event) => onChange({ ...draft, description: event.target.value })}
        />
      </FormField>

      {/* Trigger & Action Type */}
      <div className="grid gap-3 sm:grid-cols-2">
        <FormField label="执行时机">
          <select
            className="w-full h-8 px-3 rounded-md text-[12px]"
            style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-medium)" }}
            value={draft.event}
            onChange={(event) => onChange({ ...draft, event: event.target.value as AssistantHookDraft["event"] })}
          >
            {ASSISTANT_HOOK_EVENT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </FormField>

        <FormField label="动作类型">
          <select
            className="w-full h-8 px-3 rounded-md text-[12px]"
            style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-medium)" }}
            value={draft.actionType}
            onChange={(event) => onChange({ ...draft, actionType: event.target.value as AssistantHookDraft["actionType"] })}
          >
            {ASSISTANT_HOOK_ACTION_TYPE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </FormField>
      </div>

      {/* Action Config */}
      {draft.actionType === "agent" ? (
        <div className="space-y-4">
          <FormField label="选择 Agent">
            <select
              className="w-full h-8 px-3 rounded-md text-[12px]"
              style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-medium)" }}
              value={draft.agentId}
              onChange={(event) => onChange({ ...draft, agentId: event.target.value })}
            >
              <option value="">请选择 Agent</option>
              {(agentOptions ?? []).map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
            <p className="text-[10px] mt-1" style={{ color: agentErrorMessage ? "var(--accent-danger)" : "var(--text-tertiary)" }}>
              {agentErrorMessage ?? "这个 Agent 会在指定时机自动执行。"}
            </p>
          </FormField>

          <JsonTextAreaField
            emptyValue={{}}
            helpText="需要手动映射时再填写；留空就按默认方式执行。"
            label="输入映射"
            parseValue={validateAssistantHookStringMap}
            value={draft.inputMapping}
            onChange={(value) => onChange({ ...draft, inputMapping: value ?? {} })}
            onErrorChange={(message) => onFieldErrorChange("agentInputMapping", message)}
          />
        </div>
      ) : (
        <div className="space-y-4">
          <FormField label="选择 MCP">
            <select
              className="w-full h-8 px-3 rounded-md text-[12px]"
              style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-medium)" }}
              value={draft.serverId}
              onChange={(event) => onChange({ ...draft, serverId: event.target.value })}
            >
              <option value="">请选择 MCP</option>
              {(mcpOptions ?? []).map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
            <p className="text-[10px] mt-1" style={{ color: mcpErrorMessage ? "var(--accent-danger)" : "var(--text-tertiary)" }}>
              {mcpErrorMessage ?? "先选一个你自己的 MCP，再填写要调用的工具名称。"}
            </p>
          </FormField>

          <FormField label="工具名称">
            <input
              className="w-full h-8 px-3 rounded-md text-[12px]"
              style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-medium)" }}
              maxLength={120}
              placeholder="例如：search_news"
              value={draft.toolName}
              onChange={(event) => onChange({ ...draft, toolName: event.target.value })}
            />
          </FormField>

          <JsonTextAreaField
            emptyValue={{}}
            helpText="这里填写固定参数；需要从当前聊天里取值时，用下面的输入映射。"
            label="调用参数"
            parseValue={validateAssistantHookJsonObject}
            value={draft.arguments}
            onChange={(value) => onChange({ ...draft, arguments: value ?? {} })}
            onErrorChange={(message) => onFieldErrorChange("arguments", message)}
          />

          <JsonTextAreaField
            emptyValue={{}}
            helpText='例如：{ "query": "request.user_input" }'
            label="输入映射"
            parseValue={validateAssistantHookStringMap}
            value={draft.inputMapping}
            onChange={(value) => onChange({ ...draft, inputMapping: value ?? {} })}
            onErrorChange={(message) => onFieldErrorChange("inputMapping", message)}
          />
        </div>
      )}

      {/* Preview */}
      <div
        className="rounded-md p-3"
        style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}
      >
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-medium" style={{ color: "var(--text-secondary)" }}>保存后的文件</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: "var(--bg-surface)", color: "var(--text-tertiary)" }}>{ASSISTANT_HOOK_FILE_LABEL}</span>
        </div>
        <pre
          className="text-[11px] leading-4 overflow-auto rounded px-2 py-2"
          style={{ background: "var(--bg-canvas)", color: "var(--text-secondary)", maxHeight: "160px" }}
        >
          {buildAssistantHookDocumentPreview(draft, {})}
        </pre>
      </div>
    </div>
  );
}

function RawHookEditor({
  agentErrorMessage,
  agentOptions,
  documentError,
  documentValue,
  mode,
  mcpErrorMessage,
  mcpOptions,
  onChange,
}: Readonly<{
  agentErrorMessage?: string | null;
  agentOptions?: { label: string; value: string; description?: string }[];
  documentError: string | null;
  documentValue: string;
  mode: "create" | "edit";
  mcpErrorMessage?: string | null;
  mcpOptions?: { label: string; value: string; description?: string }[];
  onChange: (value: string) => void;
}>) {
  return (
    <div className="space-y-4">
      <FormField label="HOOK.yaml">
        <textarea
          className="w-full px-3 py-2 rounded-md text-[12px] resize-y font-mono"
          style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-medium)", minHeight: "320px" }}
          spellCheck={false}
          value={documentValue}
          onChange={(event) => onChange(event.target.value)}
        />
        <p className="text-[10px] mt-1" style={{ color: "var(--text-tertiary)" }}>按事件和动作来写，保存后立即生效。</p>
      </FormField>

      <div
        className="rounded-md p-3"
        style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}
      >
        <p className="text-[11px] font-medium mb-2" style={{ color: "var(--text-secondary)" }}>文件约定</p>
        <p className="text-[11px] leading-4" style={{ color: "var(--text-tertiary)" }}>
          当前只支持 before_assistant_response 和 after_assistant_response 两个事件。
        </p>
        <p className="text-[11px] leading-4 mt-1" style={{ color: "var(--text-tertiary)" }}>
          动作类型只支持 agent 或 mcp。
        </p>
        <p className="text-[11px] leading-4 mt-1" style={{ color: "var(--text-tertiary)" }}>
          author / priority / timeout / trigger.node_types 目前是固定字段，暂不支持自定义。
        </p>
        {mode === "create" ? (
          <p className="mt-2 text-[11px]" style={{ color: "var(--accent-warning)" }}>
            第一次保存后，系统会自动补上这份 Hook 的 id。
          </p>
        ) : null}
        {documentError ? (
          <p className="mt-2 rounded-md px-3 py-2 text-[11px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
            {documentError}
          </p>
        ) : null}
      </div>

      {/* References */}
      <div className="grid gap-3 sm:grid-cols-2">
        <ReferenceCard
          emptyText="还没有可选 Agent。"
          errorMessage={agentErrorMessage}
          items={agentOptions}
          title="可用 Agent"
        />
        <ReferenceCard
          emptyText="还没有可选 MCP。"
          errorMessage={mcpErrorMessage}
          items={mcpOptions}
          title="可用 MCP"
        />
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

function ReferenceCard({
  emptyText,
  errorMessage,
  items,
  title,
}: Readonly<{
  emptyText: string;
  errorMessage?: string | null;
  items?: { label: string; value: string; description?: string }[];
  title: string;
}>) {
  return (
    <div
      className="rounded-md p-3"
      style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}
    >
      <p className="text-[11px] font-medium mb-2" style={{ color: "var(--text-secondary)" }}>{title}</p>
      {errorMessage ? (
        <p className="mb-2 rounded-md px-3 py-2 text-[11px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
          {errorMessage}
        </p>
      ) : null}
      <div className="space-y-1.5">
        {(items ?? []).length === 0 ? (
          <div className="rounded px-2 py-1.5 text-[11px]" style={{ background: "var(--bg-canvas)", color: "var(--text-tertiary)" }}>
            {emptyText}
          </div>
        ) : (
          (items ?? []).map((item) => (
            <div className="flex items-center justify-between px-2 py-1.5 rounded" style={{ background: "var(--bg-canvas)" }} key={item.value}>
              <span className="text-[11px]" style={{ color: "var(--text-primary)" }}>{item.label}</span>
              <span className="text-[10px] font-mono" style={{ color: "var(--text-tertiary)" }}>{item.value}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function applyDraft(
  draft: AssistantHookDraft,
  hookId: string | null,
  setDraft: (draft: AssistantHookDraft) => void,
  setDocumentValue: (value: string) => void,
  setDocumentError: (value: string | null) => void,
) {
  setDraft(draft);
  setDocumentValue(buildAssistantHookDocumentPreview(draft, { hookId }));
  setDocumentError(null);
}

function applyDocument(
  value: string,
  hookId: string | null,
  setDraft: (draft: AssistantHookDraft) => void,
  setDocumentValue: (value: string) => void,
  setDocumentError: (value: string | null) => void,
) {
  setDocumentValue(value);
  try {
    setDraft(parseAssistantHookDocument(value, hookId));
    setDocumentError(null);
  } catch (error) {
    setDocumentError(error instanceof Error ? error.message : "HOOK.yaml 解析失败。");
  }
}
