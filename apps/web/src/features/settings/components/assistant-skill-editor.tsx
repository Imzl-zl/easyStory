"use client";

import { useEffect, useState } from "react";

import type { AssistantSkillDetail } from "@/lib/api/types";

import {
  AssistantDocumentModeToggle,
  type AssistantDocumentEditMode,
} from "./assistant-document-mode-toggle";
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
} from "./assistant-skills-support";

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
      className="panel-muted space-y-10 p-10"
      onSubmit={(event) => {
        event.preventDefault();
      onSubmit(draft);
      }}
    >
      <AssistantDocumentModeToggle
        description="新手可以先用可视化编辑；熟悉后也可以直接改 SKILL.md。"
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
          onChange={(value) =>
            applySkillDocument(
              value,
              detail?.id ?? null,
              setDraft,
              setDocumentValue,
              setDocumentError,
            )
          }
        />
      )}
      <div className="flex flex-wrap items-center justify-end gap-2">
        {documentError ? (
          <p className="mr-auto rounded-2xl bg-[rgba(178,65,46,0.08)] px-3 py-2 text-[12px] leading-5 text-[var(--accent-danger)]">
            {documentError}
          </p>
        ) : null}
        <button className="ink-button" disabled={isPending || !isDirty || Boolean(documentError)} type="submit">
          {isPending ? "保存中..." : mode === "create" ? "创建 Skill" : "保存修改"}
        </button>
        <button
          className="ink-button-secondary"
          disabled={isPending || !isDirty}
          type="button"
          onClick={() => resetEditor(detail, setDraft, setDocumentValue, setDocumentError)}
        >
          还原
        </button>
        {mode === "edit" && onDelete ? (
          <button
            className="ink-button-secondary"
            disabled={isPending}
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
    <>
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.02fr)_minmax(320px,0.98fr)]">
        <div className="space-y-4">
          <div className="rounded-2xl bg-[rgba(248,243,235,0.92)] px-4 py-3 text-xs leading-6 text-[var(--text-secondary)]">
            把常用聊天方式写成一份长期说明就行。重点告诉助手应该怎么帮你，不需要去描述系统实现。
          </div>
          <label className="block space-y-2">
            <span className="text-sm font-medium text-[var(--text-primary)]">名称</span>
            <input className="ink-input" maxLength={80} placeholder="例如：故事方向助手" value={draft.name} onChange={(event) => onChange({ ...draft, name: event.target.value })} />
          </label>
          <label className="block space-y-2">
            <span className="text-sm font-medium text-[var(--text-primary)]">一句说明</span>
            <textarea className="ink-input min-h-[88px]" maxLength={280} placeholder="例如：适合先陪我收拢方向，再一点点追问。" value={draft.description} onChange={(event) => onChange({ ...draft, description: event.target.value })} />
          </label>
          <label className="flex items-start gap-3 rounded-2xl border border-[var(--line-soft)] bg-[rgba(255,255,255,0.7)] px-4 py-3">
            <input checked={draft.enabled} className="mt-1 size-4 shrink-0 accent-[var(--accent-ink)]" type="checkbox" onChange={(event) => onChange({ ...draft, enabled: event.target.checked })} />
            <span className="space-y-1">
              <span className="block text-sm font-medium text-[var(--text-primary)]">启用</span>
              <span className="block text-[12px] leading-5 text-[var(--text-secondary)]">关闭后不会出现在聊天切换里，但文件会保留。</span>
            </span>
          </label>
        </div>
        <SkillHelperCards
          draft={draft}
          onChange={onChange}
          showPreview
          skillId={skillId}
        />
      </div>
      <label className="block space-y-2">
        <span className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-sm font-medium text-[var(--text-primary)]">正文</span>
          <span className="text-[12px] leading-5 text-[var(--text-secondary)]">建议写成一份长期说明，而不是一次性的提问。</span>
        </span>
        <textarea className="ink-input min-h-[320px] text-[13px] leading-7" placeholder={"例如：\n你是一位擅长帮新手收拢故事方向的写作助手。\n先给 2 到 3 个具体方向，再告诉我你最推荐哪一个。\n如果信息还不够，每次只追问一个关键问题。\n\n用户输入：{{ user_input }}"} spellCheck={false} value={draft.content} onChange={(event) => onChange({ ...draft, content: event.target.value })} />
      </label>
    </>
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
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1.02fr)_minmax(320px,0.98fr)]">
      <label className="block space-y-2">
        <span className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-sm font-medium text-[var(--text-primary)]">SKILL.md</span>
          <span className="text-[12px] leading-5 text-[var(--text-secondary)]">按约定直接写，保存后立即生效。</span>
        </span>
        <textarea className="ink-input min-h-[420px] font-mono text-[12px] leading-6" spellCheck={false} value={documentValue} onChange={(event) => onChange(event.target.value)} />
      </label>
        <div className="space-y-3">
          <div className="rounded-[24px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.72)] px-4 py-4">
          <p className="text-sm font-medium text-[var(--text-primary)]">文件约定</p>
          <p className="mt-1 text-[12px] leading-5 text-[var(--text-secondary)]">
            支持标准 Markdown frontmatter。`name`、`enabled`、`description`、`model` 都能直接写；多行说明可用 `description: |`。
          </p>
          {mode === "create" ? (
            <p className="mt-3 rounded-2xl bg-[rgba(183,121,31,0.08)] px-4 py-3 text-xs leading-6 text-[var(--accent-warning)]">
              第一次保存后，系统会自动补上这份 Skill 的 id。
            </p>
          ) : null}
          {documentError ? (
            <p className="mt-3 rounded-2xl bg-[rgba(178,65,46,0.08)] px-3 py-2 text-[12px] leading-5 text-[var(--accent-danger)]">
              当前文件还没写对，修正后才能保存。
            </p>
          ) : null}
        </div>
        <SkillHelperCards draft={parseDraftFromRawValue(documentValue)} showPreview={false} skillId={null} />
      </div>
    </div>
  );
}

function SkillHelperCards({
  draft,
  onChange,
  showPreview,
  skillId,
}: Readonly<{
  draft: AssistantSkillDraft;
  onChange?: (draft: AssistantSkillDraft) => void;
  showPreview: boolean;
  skillId: string | null;
}>) {
  return (
    <div className="space-y-3">
      {showPreview ? (
        <div className="rounded-[24px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.72)] p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-[var(--text-primary)]">保存后的文件</p>
              <p className="mt-1 text-[12px] leading-5 text-[var(--text-secondary)]">右侧会同步预览这份 Skill 最终保存成什么样。</p>
            </div>
            <span className="rounded-full bg-[rgba(248,243,235,0.92)] px-3 py-1 text-[12px] font-medium text-[var(--text-secondary)]">{ASSISTANT_SKILL_FILE_LABEL}</span>
          </div>
          <pre className="mt-3 max-h-[320px] overflow-auto rounded-[18px] bg-[rgba(248,243,235,0.84)] px-4 py-4 text-[12px] leading-6 text-[var(--text-primary)]">{buildAssistantSkillDocumentPreview(draft, { skillId })}</pre>
        </div>
      ) : null}
      <div className="rounded-[24px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.72)] p-4">
        <div>
          <p className="text-sm font-medium text-[var(--text-primary)]">可直接用的变量</p>
          <p className="mt-1 text-[12px] leading-5 text-[var(--text-secondary)]">这里保留了聊天最常用的两个变量，直接写进正文就能用。</p>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {ASSISTANT_SKILL_VARIABLE_TIPS.map((item) => (
            <span className="rounded-full bg-[rgba(46,111,106,0.08)] px-3 py-1 text-[12px] font-medium text-[var(--accent-ink)]" key={item}>
              {item}
            </span>
          ))}
        </div>
        <div className="mt-3 rounded-2xl bg-[rgba(248,243,235,0.92)] px-4 py-3 text-xs leading-6 text-[var(--text-secondary)]">
          常见写法：先规定语气和做事方式，再在正文里引用 <code>{"{{ user_input }}"}</code>；
          如果你希望助手参考前文，再加上 <code>{"{{ conversation_history }}"}</code>。
        </div>
        <details className="mt-3 rounded-2xl border border-[var(--line-soft)] bg-[rgba(248,243,235,0.78)]">
          <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-[var(--text-primary)]">可选：覆盖默认模型</summary>
          <div className="grid gap-3 border-t border-[var(--line-soft)] px-4 py-4 md:grid-cols-3">
            <label className="space-y-2">
              <span className="text-[12px] font-medium text-[var(--text-primary)]">默认连接</span>
              <input className="ink-input" placeholder="留空则跟随 AI 偏好" readOnly={!onChange} value={draft.defaultProvider} onChange={(event) => onChange?.({ ...draft, defaultProvider: event.target.value })} />
            </label>
            <label className="space-y-2">
              <span className="text-[12px] font-medium text-[var(--text-primary)]">默认模型</span>
              <input className="ink-input" placeholder="例如：claude-sonnet-4" readOnly={!onChange} value={draft.defaultModelName} onChange={(event) => onChange?.({ ...draft, defaultModelName: event.target.value })} />
            </label>
            <label className="space-y-2">
              <span className="text-[12px] font-medium text-[var(--text-primary)]">单次回复上限</span>
              <input className="ink-input" inputMode="numeric" placeholder="留空则跟随默认设置" readOnly={!onChange} value={draft.defaultMaxOutputTokens} onChange={(event) => onChange?.({ ...draft, defaultMaxOutputTokens: sanitizeAssistantSkillMaxOutputTokensInput(event.target.value) })} />
            </label>
          </div>
        </details>
      </div>
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

function parseDraftFromRawValue(value: string) {
  try {
    return parseAssistantSkillDocument(value);
  } catch {
    return createEmptyAssistantSkillDraft();
  }
}
