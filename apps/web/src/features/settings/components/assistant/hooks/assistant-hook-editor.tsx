"use client";

import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import type { AssistantHookDetail } from "@/lib/api/types";

import {
  AssistantDocumentModeToggle,
  type AssistantDocumentEditMode,
} from "@/features/settings/components/assistant/common/assistant-document-mode-toggle";
import {
  AssistantHookGuidedEditor,
  type AssistantHookFieldErrorKey,
} from "@/features/settings/components/assistant/hooks/assistant-hook-guided-editor";
import { AssistantHookRawEditor } from "@/features/settings/components/assistant/hooks/assistant-hook-raw-editor";
import {
  ASSISTANT_HOOK_FILE_LABEL,
  buildAssistantHookDocumentPreview,
  createEmptyAssistantHookDraft,
  isAssistantHookDirty,
  parseAssistantHookDocument,
  toAssistantHookDraft,
  type AssistantHookDraft,
} from "@/features/settings/components/assistant/hooks/assistant-hooks-support";

type AssistantHookEditorProps = {
  agentErrorMessage?: string | null;
  agentOptions: { label: string; value: string; description?: string }[];
  detail: AssistantHookDetail | null;
  isPending: boolean;
  mcpErrorMessage?: string | null;
  mcpOptions: { label: string; value: string; description?: string }[];
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
  const [fieldErrors, setFieldErrors] = useState<
    Partial<Record<AssistantHookFieldErrorKey, string | null>>
  >({});
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
    <form className="panel-muted space-y-4 p-4" onSubmit={(event) => submitDraft(event, draft, onSubmit)}>
      <AssistantDocumentModeToggle
        description="可以用可视化方式配置自动动作，也可以直接按 HOOK.yaml 的格式来写。"
        fileLabel={ASSISTANT_HOOK_FILE_LABEL}
        guidedDisabled={Boolean(documentError)}
        mode={editorMode}
        onChange={setEditorMode}
      />
      {editorMode === "guided" ? (
        <AssistantHookGuidedEditor
          agentErrorMessage={agentErrorMessage}
          agentOptions={agentOptions}
          draft={draft}
          mcpErrorMessage={mcpErrorMessage}
          mcpOptions={mcpOptions}
          preview={documentValue}
          onChange={(nextDraft) =>
            applyDraft(nextDraft, detail?.id ?? null, setDraft, setDocumentValue, setDocumentError)
          }
          onFieldErrorChange={(field, message) =>
            setFieldErrors((current) => ({ ...current, [field]: message }))
          }
        />
      ) : (
        <AssistantHookRawEditor
          agentErrorMessage={agentErrorMessage}
          agentOptions={agentOptions}
          documentError={documentError}
          documentValue={documentValue}
          mode={mode}
          mcpErrorMessage={mcpErrorMessage}
          mcpOptions={mcpOptions}
          onChange={(value) =>
            applyDocument(value, detail?.id ?? null, setDraft, setDocumentValue, setDocumentError)
          }
        />
      )}
      <div className="flex flex-wrap items-center justify-end gap-2">
        {hasFieldError || documentError ? (
          <p className="mr-auto rounded-2xl bg-[rgba(178,65,46,0.08)] px-3 py-2 text-[12px] leading-5 text-[var(--accent-danger)]">
            {documentError ?? "请先修正上面的格式问题，再保存。"}
          </p>
        ) : null}
        <button className="ink-button" disabled={isPending || !isDirty || hasFieldError || Boolean(documentError)} type="submit">
          {isPending ? "保存中..." : mode === "create" ? "创建 Hook" : "保存修改"}
        </button>
        <button className="ink-button-secondary" disabled={isPending || !isDirty} type="button" onClick={() => { const nextDraft = buildInitialDraft(detail); setDraft(nextDraft); setDocumentValue(buildAssistantHookDocumentPreview(nextDraft, { hookId: detail?.id ?? null })); setDocumentError(null); setFieldErrors({}); }}>
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

function buildInitialDraft(detail: AssistantHookDetail | null) {
  return detail ? toAssistantHookDraft(detail) : createEmptyAssistantHookDraft();
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

function submitDraft(
  event: FormEvent<HTMLFormElement>,
  draft: AssistantHookDraft,
  onSubmit: (draft: AssistantHookDraft) => void,
) {
  event.preventDefault();
  onSubmit(draft);
}
