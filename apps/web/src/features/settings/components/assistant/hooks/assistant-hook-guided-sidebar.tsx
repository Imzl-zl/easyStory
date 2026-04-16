"use client";

import {
  ASSISTANT_HOOK_FILE_LABEL,
  resolveAssistantHookActionLabel,
  resolveAssistantHookEventLabel,
  resolveAssistantHookTargetLabel,
  type AssistantHookDraft,
} from "@/features/settings/components/assistant/hooks/assistant-hooks-support";

type HookOption = { label: string; value: string; description?: string };

export function HookGuidedSidebar({
  agentOptions,
  draft,
  mcpOptions,
  preview,
}: Readonly<{
  agentOptions: HookOption[];
  draft: AssistantHookDraft;
  mcpOptions: HookOption[];
  preview: string;
}>) {
  return (
    <div className="space-y-3">
      <HookPreviewCard preview={preview} />
      <HookSummaryCard
        agentLabel={findOptionLabel(agentOptions, draft.agentId)}
        draft={draft}
        mcpLabel={findOptionLabel(mcpOptions, draft.serverId)}
      />
    </div>
  );
}

function HookSummaryCard({
  agentLabel,
  draft,
  mcpLabel,
}: Readonly<{
  agentLabel: string | null;
  draft: AssistantHookDraft;
  mcpLabel: string | null;
}>) {
  const targetLabel = resolveAssistantHookTargetLabel(
    draft.actionType === "agent"
      ? { action_type: "agent", agent_id: draft.agentId, input_mapping: draft.inputMapping }
      : {
          action_type: "mcp",
          arguments: draft.arguments,
          input_mapping: draft.inputMapping,
          server_id: draft.serverId,
          tool_name: draft.toolName,
        },
    { agentLabel, mcpLabel },
  );
  return (
    <div className="rounded-3xl bg-glass shadow-glass px-4 py-3">
      <p className="text-sm font-medium text-text-primary">当前效果</p>
      <p className="mt-1 text-[12px] leading-5 text-text-secondary">
        {resolveAssistantHookEventLabel(draft.event)}时，自动调用
        {resolveAssistantHookActionLabel(draft.actionType)}：{targetLabel}
      </p>
    </div>
  );
}

function HookPreviewCard({ preview }: Readonly<{ preview: string }>) {
  return (
    <div className="rounded-3xl bg-glass shadow-glass p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-text-primary">保存后的文件</p>
          <p className="mt-1 text-[12px] leading-5 text-text-secondary">
            右侧会同步预览这份 Hook 最终保存成什么样。
          </p>
        </div>
        <span className="rounded-pill bg-glass-heavy px-3 py-1 text-[12px] font-medium text-text-secondary">
          {ASSISTANT_HOOK_FILE_LABEL}
        </span>
      </div>
      <pre className="mt-3 max-h-[320px] overflow-auto rounded-2xl bg-glass px-4 py-4 text-[12px] leading-6 text-text-primary">
        {preview}
      </pre>
    </div>
  );
}

function findOptionLabel(options: ReadonlyArray<HookOption>, value: string) {
  return options.find((item) => item.value === value)?.label ?? null;
}
