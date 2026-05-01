"use client";

import { useEffect, useState } from "react";

import type { AssistantAgentDetail } from "@/lib/api/types";

import {
  AssistantDocumentModeToggle,
  type AssistantDocumentEditMode,
} from "@/features/settings/components/assistant/common/assistant-document-mode-toggle";
import type { AssistantAgentOption } from "@/features/settings/components/assistant/agents/assistant-agent-editor-types";
import {
  ASSISTANT_AGENT_FILE_LABEL,
  buildAssistantAgentDocumentPreview,
  createEmptyAssistantAgentDraft,
  isAssistantAgentDirty,
  parseAssistantAgentDocument,
  sanitizeAssistantAgentMaxOutputTokensInput,
  toAssistantAgentDraft,
  type AssistantAgentDraft,
} from "@/features/settings/components/assistant/agents/assistant-agents-support";

type AssistantAgentEditorProps = {
  detail: AssistantAgentDetail | null;
  isPending: boolean;
  mode: "create" | "edit";
  skillErrorMessage?: string | null;
  skillOptions: AssistantAgentOption[];
  onDelete?: () => void;
  onDirtyChange?: (isDirty: boolean) => void;
  onSubmit: (draft: AssistantAgentDraft) => void;
};

export function AssistantAgentEditor({
  detail,
  isPending,
  mode,
  skillErrorMessage,
  skillOptions,
  onDelete,
  onDirtyChange,
  onSubmit,
}: AssistantAgentEditorProps) {
  const [draft, setDraft] = useState<AssistantAgentDraft>(() => buildInitialDraft(detail));
  const [editorMode, setEditorMode] = useState<AssistantDocumentEditMode>("guided");
  const [documentValue, setDocumentValue] = useState(() =>
    buildAssistantAgentDocumentPreview(buildInitialDraft(detail), { agentId: detail?.id ?? null }),
  );
  const [documentError, setDocumentError] = useState<string | null>(null);
  const isDirty = Boolean(documentError) || isAssistantAgentDirty(draft, detail);

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
        fileLabel={ASSISTANT_AGENT_FILE_LABEL}
        guidedDisabled={Boolean(documentError)}
        mode={editorMode}
        onChange={setEditorMode}
      />

      {editorMode === "guided" ? (
        <GuidedAgentEditor
          agentId={detail?.id ?? null}
          draft={draft}
          skillErrorMessage={skillErrorMessage}
          skillOptions={skillOptions}
          onChange={(nextDraft) => applyDraft(nextDraft, detail?.id ?? null, setDraft, setDocumentValue, setDocumentError)}
        />
      ) : (
        <RawAgentEditor
          documentError={documentError}
          documentValue={documentValue}
          mode={mode}
          skillErrorMessage={skillErrorMessage}
          skillOptions={skillOptions}
          onChange={(value) => applyAgentDocument(value, detail?.id ?? null, setDraft, setDocumentValue, setDocumentError)}
        />
      )}

      {/* Actions */}
      <div className="flex gap-2 pt-1">
        {documentError ? (
          <p className="mr-auto rounded-md px-3 py-2 text-[12px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
            {documentError}
          </p>
        ) : null}
        <button
          className="h-8 px-4 rounded-md text-[12px] font-medium transition-colors"
          disabled={isPending || !isDirty || Boolean(documentError)}
          style={{
            background: isDirty && !documentError ? "var(--accent-primary)" : "var(--line-soft)",
            color: isDirty && !documentError ? "var(--text-on-accent)" : "var(--text-tertiary)",
          }}
          type="submit"
        >
          {isPending ? "保存中..." : mode === "create" ? "创建 Agent" : "保存修改"}
        </button>
        <button
          className="h-8 px-4 rounded-md text-[12px] font-medium"
          disabled={isPending || !isDirty}
          onClick={() => resetEditor(detail, setDraft, setDocumentValue, setDocumentError)}
          style={{ background: "var(--bg-surface)", color: "var(--text-secondary)", border: "1px solid var(--line-medium)" }}
          type="button"
        >
          还原
        </button>
        {mode === "edit" && onDelete ? (
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

function buildInitialDraft(detail: AssistantAgentDetail | null) {
  return detail ? toAssistantAgentDraft(detail) : createEmptyAssistantAgentDraft();
}

function GuidedAgentEditor({
  agentId,
  draft,
  skillErrorMessage,
  skillOptions,
  onChange,
}: Readonly<{
  agentId: string | null;
  draft: AssistantAgentDraft;
  skillErrorMessage?: string | null;
  skillOptions: AssistantAgentOption[];
  onChange: (draft: AssistantAgentDraft) => void;
}>) {
  return (
    <div className="space-y-4">
      {/* Info Banner */}
      <div className="rounded-md px-3 py-2 text-[11px]" style={{ background: "var(--accent-primary-soft)", color: "var(--accent-primary)", border: "1px solid var(--accent-primary-soft)" }}>
        Agent 更像"固定好的助手角色"。你只需要写清楚它应该怎么陪你，不需要写技术说明。
      </div>

      {/* Basic Info */}
      <div className="grid gap-3 sm:grid-cols-2">
        <FormField label="名称">
          <input
            className="w-full h-8 px-3 rounded-md text-[12px]"
            style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-medium)" }}
            maxLength={80}
            placeholder="例如：温柔陪跑"
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
          placeholder="例如：适合先陪我找方向，再慢慢追问。"
          value={draft.description}
          onChange={(event) => onChange({ ...draft, description: event.target.value })}
        />
      </FormField>

      {/* Skill Binding */}
      <FormField label="绑定 Skill">
        <select
          className="w-full h-8 px-3 rounded-md text-[12px]"
          style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-medium)" }}
          value={draft.skillId}
          onChange={(event) => onChange({ ...draft, skillId: event.target.value })}
        >
          {skillOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <p className="text-[10px] mt-1" style={{ color: skillErrorMessage ? "var(--accent-danger)" : "var(--text-tertiary)" }}>
          {skillErrorMessage ?? "Agent 会沿用这份 Skill 来组织聊天正文，再叠加你在下面写的角色说明。"}
        </p>
      </FormField>

      {/* System Prompt */}
      <FormField label="角色说明">
        <textarea
          className="w-full px-3 py-2 rounded-md text-[12px] resize-y"
          style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-medium)", minHeight: "200px" }}
          maxLength={20000}
          placeholder={"例如：\n你是一位擅长陪新手收拢故事方向的长期创作搭子。\n先给结论，再展开。\n如果信息还不够，每次只追问一个关键问题。"}
          spellCheck={false}
          value={draft.systemPrompt}
          onChange={(event) => onChange({ ...draft, systemPrompt: event.target.value })}
        />
        <p className="text-[10px] mt-1" style={{ color: "var(--text-tertiary)" }}>写清楚这个 Agent 应该怎么陪你聊天</p>
      </FormField>

      {/* Model Override */}
      <div
        className="rounded-md p-3 space-y-3"
        style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}
      >
        <p className="text-[11px] font-medium" style={{ color: "var(--text-secondary)" }}>可选：覆盖默认模型</p>
        <div className="grid gap-3 sm:grid-cols-3">
          <FormField label="默认连接">
            <input
              className="w-full h-8 px-3 rounded-md text-[12px]"
              style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-medium)" }}
              placeholder="留空则跟随 AI 偏好"
              value={draft.defaultProvider}
              onChange={(event) => onChange({ ...draft, defaultProvider: event.target.value })}
            />
          </FormField>
          <FormField label="默认模型">
            <input
              className="w-full h-8 px-3 rounded-md text-[12px]"
              style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-medium)" }}
              placeholder="例如：claude-sonnet-4"
              value={draft.defaultModelName}
              onChange={(event) => onChange({ ...draft, defaultModelName: event.target.value })}
            />
          </FormField>
          <FormField label="单次回复上限">
            <input
              className="w-full h-8 px-3 rounded-md text-[12px]"
              style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-medium)" }}
              inputMode="numeric"
              placeholder="留空则跟随默认设置"
              value={draft.defaultMaxOutputTokens}
              onChange={(event) => onChange({ ...draft, defaultMaxOutputTokens: sanitizeAssistantAgentMaxOutputTokensInput(event.target.value) })}
            />
          </FormField>
        </div>
      </div>

      {/* Preview */}
      <div
        className="rounded-md p-3"
        style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}
      >
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-medium" style={{ color: "var(--text-secondary)" }}>保存后的文件</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: "var(--bg-surface)", color: "var(--text-tertiary)" }}>{ASSISTANT_AGENT_FILE_LABEL}</span>
        </div>
        <pre
          className="text-[11px] leading-4 overflow-auto rounded px-2 py-2"
          style={{ background: "var(--bg-canvas)", color: "var(--text-secondary)", maxHeight: "160px" }}
        >
          {buildAssistantAgentDocumentPreview(draft, { agentId })}
        </pre>
      </div>
    </div>
  );
}

function RawAgentEditor({
  documentError,
  documentValue,
  mode,
  skillErrorMessage,
  skillOptions,
  onChange,
}: Readonly<{
  documentError: string | null;
  documentValue: string;
  mode: "create" | "edit";
  skillErrorMessage?: string | null;
  skillOptions: AssistantAgentOption[];
  onChange: (value: string) => void;
}>) {
  return (
    <div className="space-y-4">
      <FormField label="AGENT.md">
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
          frontmatter 需要带上 name、skill_id，需要覆盖模型时再补 model。
        </p>
        {mode === "create" ? (
          <p className="mt-2 text-[11px]" style={{ color: "var(--accent-warning)" }}>
            第一次保存后，系统会自动补上这份 Agent 的 id。
          </p>
        ) : null}
        {documentError ? (
          <p className="mt-2 rounded-md px-3 py-2 text-[11px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
            {documentError}
          </p>
        ) : null}
        {skillErrorMessage ? (
          <p className="mt-2 rounded-md px-3 py-2 text-[11px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
            {skillErrorMessage}
          </p>
        ) : null}
      </div>

      {/* Skill Reference */}
      <div
        className="rounded-md p-3"
        style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}
      >
        <p className="text-[11px] font-medium mb-2" style={{ color: "var(--text-secondary)" }}>可用 Skill 参考</p>
        <div className="space-y-1.5">
          {skillOptions.map((item) => (
            <div className="flex items-center justify-between px-2 py-1.5 rounded" style={{ background: "var(--bg-canvas)" }} key={item.value}>
              <span className="text-[11px]" style={{ color: "var(--text-primary)" }}>{item.label}</span>
              <span className="text-[10px] font-mono" style={{ color: "var(--text-tertiary)" }}>{item.value}</span>
            </div>
          ))}
        </div>
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
  draft: AssistantAgentDraft,
  agentId: string | null,
  setDraft: (draft: AssistantAgentDraft) => void,
  setDocumentValue: (value: string) => void,
  setDocumentError: (value: string | null) => void,
) {
  setDraft(draft);
  setDocumentValue(buildAssistantAgentDocumentPreview(draft, { agentId }));
  setDocumentError(null);
}

function applyAgentDocument(
  value: string,
  agentId: string | null,
  setDraft: (draft: AssistantAgentDraft) => void,
  setDocumentValue: (value: string) => void,
  setDocumentError: (value: string | null) => void,
) {
  setDocumentValue(value);
  try {
    setDraft(parseAssistantAgentDocument(value, agentId));
    setDocumentError(null);
  } catch (error) {
    setDocumentError(error instanceof Error ? error.message : "AGENT.md 解析失败。");
  }
}

function resetEditor(
  detail: AssistantAgentDetail | null,
  setDraft: (draft: AssistantAgentDraft) => void,
  setDocumentValue: (value: string) => void,
  setDocumentError: (value: string | null) => void,
) {
  const nextDraft = buildInitialDraft(detail);
  setDraft(nextDraft);
  setDocumentValue(buildAssistantAgentDocumentPreview(nextDraft, { agentId: detail?.id ?? null }));
  setDocumentError(null);
}
