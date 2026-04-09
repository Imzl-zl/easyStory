"use client";

import { AgentHelperCards } from "@/features/settings/components/assistant/agents/assistant-agent-helper-cards";
import type { AssistantAgentOption } from "@/features/settings/components/assistant/agents/assistant-agent-editor-types";
import {
  AssistantSelectField,
  AssistantTextareaField,
  AssistantTextField,
  AssistantToggleField,
} from "@/features/settings/components/assistant/common/assistant-editor-primitives";
import type { AssistantAgentDraft } from "@/features/settings/components/assistant/agents/assistant-agents-support";

export function AssistantAgentGuidedEditor({
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
    <>
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.96fr)]">
        <AgentMainFields
          draft={draft}
          skillErrorMessage={skillErrorMessage}
          skillOptions={skillOptions}
          onChange={onChange}
        />
        <AgentHelperCards
          agentId={agentId}
          draft={draft}
          onChange={onChange}
          showPreview
          skillErrorMessage={skillErrorMessage}
          skillOptions={skillOptions}
        />
      </div>
      <AgentPromptField draft={draft} onChange={onChange} />
    </>
  );
}

function AgentMainFields({
  draft,
  skillErrorMessage,
  skillOptions,
  onChange,
}: Readonly<{
  draft: AssistantAgentDraft;
  skillErrorMessage?: string | null;
  skillOptions: AssistantAgentOption[];
  onChange: (draft: AssistantAgentDraft) => void;
}>) {
  return (
    <div className="space-y-4">
      <div className="rounded-2xl bg-[rgba(58,124,165,0.07)] px-4 py-3 text-[12px] leading-6 text-[var(--text-secondary)]">
        Agent 更像“固定好的助手角色”。你只需要写清楚它应该怎么陪你，不需要写技术说明。
      </div>
      <AssistantTextField
        label="名称"
        maxLength={80}
        placeholder="例如：温柔陪跑"
        value={draft.name}
        onChange={(value) => onChange({ ...draft, name: value })}
      />
      <AssistantTextareaField
        label="一句说明"
        maxLength={240}
        placeholder="例如：适合先陪我找方向，再慢慢追问。"
        value={draft.description}
        onChange={(value) => onChange({ ...draft, description: value })}
      />
      <AssistantToggleField
        checked={draft.enabled}
        description="关闭后不会出现在聊天切换里，但文件会保留。"
        label="启用"
        onChange={(checked) => onChange({ ...draft, enabled: checked })}
      />
      <AssistantSelectField
        description={
          skillErrorMessage
            ? skillErrorMessage
            : "Agent 会沿用这份 Skill 来组织聊天正文，再叠加你在下面写的角色说明。"
        }
        label="绑定 Skill"
        options={skillOptions}
        tone={skillErrorMessage ? "danger" : "default"}
        value={draft.skillId}
        onChange={(value) => onChange({ ...draft, skillId: value })}
      />
    </div>
  );
}

function AgentPromptField({
  draft,
  onChange,
}: Readonly<{
  draft: AssistantAgentDraft;
  onChange: (draft: AssistantAgentDraft) => void;
}>) {
  return (
    <AssistantTextareaField
      className="ink-input min-h-[280px] text-[13px] leading-7"
      label="角色说明"
      maxLength={20000}
      placeholder={
        "例如：\n你是一位擅长陪新手收拢故事方向的长期创作搭子。\n先给结论，再展开。\n如果信息还不够，每次只追问一个关键问题。"
      }
      value={draft.systemPrompt}
      onChange={(value) => onChange({ ...draft, systemPrompt: value })}
    />
  );
}
