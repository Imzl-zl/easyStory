"use client";

import { useEffect, useState } from "react";

import type { AssistantSkillDetail } from "@/lib/api/types";

import {
  AssistantDocumentModeToggle,
  type AssistantDocumentEditMode,
} from "@/features/settings/components/assistant/common/assistant-document-mode-toggle";
import {
  ASSISTANT_SKILL_FILE_LABEL,
  ASSISTANT_SKILL_VARIABLE_TIPS,
  buildAssistantSkillDocumentPreview,
  createEmptyAssistantSkillDraft,
  isAssistantSkillDirty,
  parseAssistantSkillDocument,
  sanitizeAssistantSkillMaxOutputTokensInput,
  toAssistantSkillDraft,
  type AssistantSkillDraft,
} from "@/features/settings/components/assistant/skills/assistant-skills-support";

type AssistantSkillEditorProps = {
  detail: AssistantSkillDetail | null;
  isPending: boolean;
  mode: "create" | "edit";
  onDelete?: () => void;
  onDirtyChange?: (isDirty: boolean) => void;
  onSubmit: (draft: AssistantSkillDraft) => void;
};

export function AssistantSkillEditor({
  detail,
  isPending,
  mode,
  onDelete,
  onDirtyChange,
  onSubmit,
}: AssistantSkillEditorProps) {
  const [draft, setDraft] = useState<AssistantSkillDraft>(() => buildInitialDraft(detail));
  const [editorMode, setEditorMode] = useState<AssistantDocumentEditMode>("guided");
  const [documentValue, setDocumentValue] = useState(() =>
    buildAssistantSkillDocumentPreview(buildInitialDraft(detail), { skillId: detail?.id ?? null }),
  );
  const [documentError, setDocumentError] = useState<string | null>(null);
  const isDirty = Boolean(documentError) || isAssistantSkillDirty(draft, detail);

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
        fileLabel={ASSISTANT_SKILL_FILE_LABEL}
        guidedDisabled={Boolean(documentError)}
        mode={editorMode}
        onChange={setEditorMode}
      />

      {editorMode === "guided" ? (
        <GuidedSkillEditor
          draft={draft}
          skillId={detail?.id ?? null}
          onChange={(nextDraft) => applyDraft(nextDraft, detail?.id ?? null, setDraft, setDocumentValue, setDocumentError)}
        />
      ) : (
        <RawSkillEditor
          documentError={documentError}
          documentValue={documentValue}
          mode={mode}
          onChange={(value) => applySkillDocument(value, detail?.id ?? null, setDraft, setDocumentValue, setDocumentError)}
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
          {isPending ? "保存中..." : mode === "create" ? "创建 Skill" : "保存修改"}
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

function buildInitialDraft(detail: AssistantSkillDetail | null) {
  return detail ? toAssistantSkillDraft(detail) : createEmptyAssistantSkillDraft();
}

function GuidedSkillEditor({
  draft,
  onChange,
  skillId,
}: Readonly<{
  draft: AssistantSkillDraft;
  onChange: (draft: AssistantSkillDraft) => void;
  skillId: string | null;
}>) {
  return (
    <div className="space-y-4">
      {/* Basic Info */}
      <div className="grid gap-3 sm:grid-cols-2">
        <FormField label="名称">
          <input
            className="w-full h-8 px-3 rounded-md text-[12px]"
            style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-medium)" }}
            maxLength={80}
            placeholder="例如：故事方向助手"
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
          maxLength={280}
          placeholder="例如：适合先陪我收拢方向，再一点点追问。"
          value={draft.description}
          onChange={(event) => onChange({ ...draft, description: event.target.value })}
        />
      </FormField>

      {/* Content */}
      <FormField label="正文">
        <textarea
          className="w-full px-3 py-2 rounded-md text-[12px] resize-y"
          style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-medium)", minHeight: "200px" }}
          placeholder={"例如：\n你是一位擅长帮新手收拢故事方向的写作助手。\n先给 2 到 3 个具体方向，再告诉我你最推荐哪一个。\n如果信息还不够，每次只追问一个关键问题。\n\n用户输入：{{ user_input }}"}
          spellCheck={false}
          value={draft.content}
          onChange={(event) => onChange({ ...draft, content: event.target.value })}
        />
        <p className="text-[10px] mt-1" style={{ color: "var(--text-tertiary)" }}>建议写成一份长期说明，而不是一次性的提问</p>
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
              onChange={(event) => onChange({ ...draft, defaultMaxOutputTokens: sanitizeAssistantSkillMaxOutputTokensInput(event.target.value) })}
            />
          </FormField>
        </div>
      </div>

      {/* Preview & Tips */}
      <div className="grid gap-3 sm:grid-cols-2">
        <div
          className="rounded-md p-3"
          style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-medium" style={{ color: "var(--text-secondary)" }}>保存后的文件</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: "var(--bg-surface)", color: "var(--text-tertiary)" }}>{ASSISTANT_SKILL_FILE_LABEL}</span>
          </div>
          <pre
            className="text-[11px] leading-4 overflow-auto rounded px-2 py-2"
            style={{ background: "var(--bg-canvas)", color: "var(--text-secondary)", maxHeight: "160px" }}
          >
            {buildAssistantSkillDocumentPreview(draft, { skillId })}
          </pre>
        </div>

        <div
          className="rounded-md p-3"
          style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-soft)" }}
        >
          <p className="text-[11px] font-medium mb-2" style={{ color: "var(--text-secondary)" }}>可直接用的变量</p>
          <div className="flex flex-wrap gap-1.5 mb-2">
            {ASSISTANT_SKILL_VARIABLE_TIPS.map((item) => (
              <span
                className="px-2 py-0.5 rounded text-[10px] font-medium"
                style={{ background: "var(--accent-primary-soft)", color: "var(--accent-primary)" }}
                key={item}
              >
                {item}
              </span>
            ))}
          </div>
          <p className="text-[10px] leading-4" style={{ color: "var(--text-tertiary)" }}>
            常见写法：先规定语气和做事方式，再在正文里引用 {"{{ user_input }}"}；如果你希望助手参考前文，再加上 {"{{ conversation_history }}"}。
          </p>
        </div>
      </div>
    </div>
  );
}

function RawSkillEditor({
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
      <FormField label="SKILL.md">
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
          支持标准 Markdown frontmatter。name、enabled、description、model 都能直接写；多行说明可用 description: |。
        </p>
        {mode === "create" ? (
          <p className="mt-2 text-[11px]" style={{ color: "var(--accent-warning)" }}>
            第一次保存后，系统会自动补上这份 Skill 的 id。
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
  draft: AssistantSkillDraft,
  skillId: string | null,
  setDraft: (draft: AssistantSkillDraft) => void,
  setDocumentValue: (value: string) => void,
  setDocumentError: (value: string | null) => void,
) {
  setDraft(draft);
  setDocumentValue(buildAssistantSkillDocumentPreview(draft, { skillId }));
  setDocumentError(null);
}

function applySkillDocument(
  value: string,
  skillId: string | null,
  setDraft: (draft: AssistantSkillDraft) => void,
  setDocumentValue: (value: string) => void,
  setDocumentError: (value: string | null) => void,
) {
  setDocumentValue(value);
  try {
    setDraft(parseAssistantSkillDocument(value, skillId));
    setDocumentError(null);
  } catch (error) {
    setDocumentError(error instanceof Error ? error.message : "SKILL.md 解析失败。");
  }
}

function resetEditor(
  detail: AssistantSkillDetail | null,
  setDraft: (draft: AssistantSkillDraft) => void,
  setDocumentValue: (value: string) => void,
  setDocumentError: (value: string | null) => void,
) {
  const nextDraft = buildInitialDraft(detail);
  setDraft(nextDraft);
  setDocumentValue(buildAssistantSkillDocumentPreview(nextDraft, { skillId: detail?.id ?? null }));
  setDocumentError(null);
}
