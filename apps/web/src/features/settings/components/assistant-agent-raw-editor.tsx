"use client";

import { AgentHelperCards, AgentRawInfoCard } from "./assistant-agent-helper-cards";
import type { AssistantAgentOption } from "./assistant-agent-editor-types";
import {
  createEmptyAssistantAgentDraft,
  parseAssistantAgentDocument,
  type AssistantAgentDraft,
} from "./assistant-agents-support";

export function AssistantAgentRawEditor({
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
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.96fr)]">
      <label className="block space-y-2">
        <span className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-sm font-medium text-[var(--text-primary)]">AGENT.md</span>
          <span className="text-[12px] leading-5 text-[var(--text-secondary)]">
            按 `skill_id` 绑定 Skill，保存后立即生效。
          </span>
        </span>
        <textarea
          className="ink-input min-h-[420px] font-mono text-[12px] leading-6"
          spellCheck={false}
          value={documentValue}
          onChange={(event) => onChange(event.target.value)}
        />
      </label>
      <div className="space-y-3">
        <AgentRawInfoCard
          documentError={documentError}
          mode={mode}
          skillErrorMessage={skillErrorMessage}
        />
        <AgentHelperCards
          agentId={null}
          draft={parseDraftFromRawValue(documentValue)}
          showPreview={false}
          skillErrorMessage={skillErrorMessage}
          skillOptions={skillOptions}
        />
      </div>
    </div>
  );
}

function parseDraftFromRawValue(value: string): AssistantAgentDraft {
  try {
    return parseAssistantAgentDocument(value);
  } catch {
    return createEmptyAssistantAgentDraft();
  }
}
