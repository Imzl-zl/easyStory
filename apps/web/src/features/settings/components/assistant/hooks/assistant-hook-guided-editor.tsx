"use client";

import type { AssistantHookDraft } from "@/features/settings/components/assistant/hooks/assistant-hooks-support";
import {
  HookGuidedFormPanel,
  type AssistantHookFieldErrorKey,
} from "@/features/settings/components/assistant/hooks/assistant-hook-guided-fields";
import { HookGuidedSidebar } from "@/features/settings/components/assistant/hooks/assistant-hook-guided-sidebar";

export type { AssistantHookFieldErrorKey } from "@/features/settings/components/assistant/hooks/assistant-hook-guided-fields";

type AssistantHookGuidedEditorProps = {
  agentErrorMessage?: string | null;
  agentOptions: { label: string; value: string; description?: string }[];
  draft: AssistantHookDraft;
  mcpErrorMessage?: string | null;
  mcpOptions: { label: string; value: string; description?: string }[];
  onChange: (draft: AssistantHookDraft) => void;
  onFieldErrorChange: (field: AssistantHookFieldErrorKey, message: string | null) => void;
  preview: string;
};

export function AssistantHookGuidedEditor({
  agentErrorMessage,
  agentOptions,
  draft,
  mcpErrorMessage,
  mcpOptions,
  onChange,
  onFieldErrorChange,
  preview,
}: Readonly<AssistantHookGuidedEditorProps>) {
  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.92fr)]">
      <HookGuidedFormPanel
        agentErrorMessage={agentErrorMessage}
        agentOptions={agentOptions}
        draft={draft}
        mcpErrorMessage={mcpErrorMessage}
        mcpOptions={mcpOptions}
        onChange={onChange}
        onFieldErrorChange={onFieldErrorChange}
      />
      <HookGuidedSidebar agentOptions={agentOptions} draft={draft} mcpOptions={mcpOptions} preview={preview} />
    </div>
  );
}
