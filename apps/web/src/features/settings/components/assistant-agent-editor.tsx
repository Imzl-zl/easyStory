"use client";

import { useEffect, useState } from "react";

import type { AssistantAgentDetail } from "@/lib/api/types";

import {
  AssistantAgentGuidedEditor,
  AssistantAgentRawEditor,
  type AssistantAgentOption,
} from "./assistant-agent-mode-editors";
import {
  AssistantDocumentModeToggle,
  type AssistantDocumentEditMode,
} from "./assistant-document-mode-toggle";
import {
  ASSISTANT_AGENT_FILE_LABEL,
  buildAssistantAgentDocumentPreview,
  createEmptyAssistantAgentDraft,
  isAssistantAgentDirty,
  parseAssistantAgentDocument,
  toAssistantAgentDraft,
  type AssistantAgentDraft,
} from "./assistant-agents-support";

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
      className="panel-muted space-y-4 p-4"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(draft);
      }}
    >
      <AssistantDocumentModeToggle
        description="可以先用可视化编辑固定角色，也可以直接按 AGENT.md 的格式来写。"
        fileLabel={ASSISTANT_AGENT_FILE_LABEL}
        guidedDisabled={Boolean(documentError)}
        mode={editorMode}
        onChange={setEditorMode}
      />
      {editorMode === "guided" ? (
        <AssistantAgentGuidedEditor
          agentId={detail?.id ?? null}
          draft={draft}
          skillErrorMessage={skillErrorMessage}
          skillOptions={skillOptions}
          onChange={(nextDraft) =>
            applyDraft(nextDraft, detail?.id ?? null, setDraft, setDocumentValue, setDocumentError)
          }
        />
      ) : (
        <AssistantAgentRawEditor
          documentError={documentError}
          documentValue={documentValue}
          mode={mode}
          skillErrorMessage={skillErrorMessage}
          skillOptions={skillOptions}
          onChange={(value) =>
            applyAgentDocument(
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
          {isPending ? "保存中..." : mode === "create" ? "创建 Agent" : "保存修改"}
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
          <button className="ink-button-secondary" disabled={isPending} type="button" onClick={onDelete}>
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
