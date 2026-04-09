"use client";

import type { AssistantAgentDraft } from "@/features/settings/components/assistant/agents/assistant-agents-support";
import {
  ASSISTANT_AGENT_FILE_LABEL,
  buildAssistantAgentDocumentPreview,
  sanitizeAssistantAgentMaxOutputTokensInput,
} from "@/features/settings/components/assistant/agents/assistant-agents-support";
import type { AssistantAgentOption } from "@/features/settings/components/assistant/agents/assistant-agent-editor-types";

export function AgentHelperCards({
  agentId,
  draft,
  onChange,
  skillErrorMessage,
  skillOptions,
  showPreview,
}: Readonly<{
  agentId: string | null;
  draft: AssistantAgentDraft;
  onChange?: (draft: AssistantAgentDraft) => void;
  skillErrorMessage?: string | null;
  skillOptions: AssistantAgentOption[];
  showPreview: boolean;
}>) {
  return (
    <div className="space-y-3">
      {showPreview ? <AgentPreviewCard agentId={agentId} draft={draft} /> : null}
      <div className="rounded-[24px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.72)] p-4">
        <p className="text-sm font-medium text-[var(--text-primary)]">可用 Skill 参考</p>
        <p className="mt-1 text-[12px] leading-5 text-[var(--text-secondary)]">
          按文件编辑时，把对应的 `skill_id` 直接写进 frontmatter 即可。
        </p>
        <AgentSkillReferenceList skillOptions={skillOptions} />
        {skillErrorMessage ? (
          <p className="mt-3 rounded-2xl bg-[rgba(178,65,46,0.08)] px-3 py-2 text-[12px] leading-5 text-[var(--accent-danger)]">
            {skillErrorMessage}
          </p>
        ) : null}
        <AgentModelOverrideFields draft={draft} onChange={onChange} />
      </div>
    </div>
  );
}

export function AgentRawInfoCard({
  documentError,
  mode,
  skillErrorMessage,
}: Readonly<{
  documentError: string | null;
  mode: "create" | "edit";
  skillErrorMessage?: string | null;
}>) {
  return (
    <div className="rounded-[24px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.72)] px-4 py-4">
      <p className="text-sm font-medium text-[var(--text-primary)]">文件约定</p>
      <p className="mt-1 text-[12px] leading-5 text-[var(--text-secondary)]">
        frontmatter 需要带上 `name`、`skill_id`，需要覆盖模型时再补 `model`。
      </p>
      {mode === "create" ? (
        <p className="mt-3 rounded-2xl bg-[rgba(248,243,235,0.84)] px-3 py-2 text-[12px] leading-5 text-[var(--text-secondary)]">
          第一次保存后，系统会自动补上这份 Agent 的 id。
        </p>
      ) : null}
      {documentError ? (
        <p className="mt-3 rounded-2xl bg-[rgba(178,65,46,0.08)] px-3 py-2 text-[12px] leading-5 text-[var(--accent-danger)]">
          当前文件还没写对，修正后才能保存。
        </p>
      ) : null}
      {skillErrorMessage ? (
        <p className="mt-3 rounded-2xl bg-[rgba(178,65,46,0.08)] px-3 py-2 text-[12px] leading-5 text-[var(--accent-danger)]">
          {skillErrorMessage}
        </p>
      ) : null}
    </div>
  );
}

function AgentPreviewCard({
  agentId,
  draft,
}: Readonly<{
  agentId: string | null;
  draft: AssistantAgentDraft;
}>) {
  return (
    <div className="rounded-[24px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.72)] p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-[var(--text-primary)]">保存后的文件</p>
          <p className="mt-1 text-[12px] leading-5 text-[var(--text-secondary)]">
            右侧会同步预览这份 Agent 最终保存成什么样。
          </p>
        </div>
        <span className="rounded-full bg-[rgba(248,243,235,0.92)] px-3 py-1 text-[12px] font-medium text-[var(--text-secondary)]">
          {ASSISTANT_AGENT_FILE_LABEL}
        </span>
      </div>
      <pre className="mt-3 max-h-[320px] overflow-auto rounded-[18px] bg-[rgba(248,243,235,0.84)] px-4 py-4 text-[12px] leading-6 text-[var(--text-primary)]">
        {buildAssistantAgentDocumentPreview(draft, { agentId })}
      </pre>
    </div>
  );
}

function AgentSkillReferenceList({
  skillOptions,
}: Readonly<{ skillOptions: AssistantAgentOption[] }>) {
  return (
    <div className="mt-3 space-y-2">
      {skillOptions.map((item) => (
        <div className="rounded-2xl bg-[rgba(248,243,235,0.84)] px-3 py-3" key={item.value}>
          <p className="text-[12px] font-medium text-[var(--text-primary)]">{item.label}</p>
          <p className="mt-1 break-all font-mono text-[11px] leading-5 text-[var(--text-secondary)]">
            {item.value}
          </p>
        </div>
      ))}
    </div>
  );
}

function AgentModelOverrideFields({
  draft,
  onChange,
}: Readonly<{
  draft: AssistantAgentDraft;
  onChange?: (draft: AssistantAgentDraft) => void;
}>) {
  return (
    <details className="mt-3 rounded-2xl border border-[var(--line-soft)] bg-[rgba(248,243,235,0.78)]">
      <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-[var(--text-primary)]">
        可选：覆盖默认模型
      </summary>
      <div className="grid gap-3 border-t border-[var(--line-soft)] px-4 py-4 md:grid-cols-3">
        <AgentModelInput
          label="默认连接"
          placeholder="留空则跟随 AI 偏好"
          readOnly={!onChange}
          value={draft.defaultProvider}
          onChange={(value) => onChange?.({ ...draft, defaultProvider: value })}
        />
        <AgentModelInput
          label="默认模型"
          placeholder="例如：claude-sonnet-4"
          readOnly={!onChange}
          value={draft.defaultModelName}
          onChange={(value) => onChange?.({ ...draft, defaultModelName: value })}
        />
        <AgentModelInput
          inputMode="numeric"
          label="单次回复上限"
          placeholder="留空则跟随默认设置"
          readOnly={!onChange}
          value={draft.defaultMaxOutputTokens}
          onChange={(value) =>
            onChange?.({
              ...draft,
              defaultMaxOutputTokens: sanitizeAssistantAgentMaxOutputTokensInput(value),
            })
          }
        />
      </div>
    </details>
  );
}

function AgentModelInput({
  inputMode,
  label,
  placeholder,
  readOnly,
  value,
  onChange,
}: Readonly<{
  inputMode?: "numeric";
  label: string;
  placeholder: string;
  readOnly: boolean;
  value: string;
  onChange: (value: string) => void;
}>) {
  return (
    <label className="space-y-2">
      <span className="text-[12px] font-medium text-[var(--text-primary)]">{label}</span>
      <input
        className="ink-input"
        inputMode={inputMode}
        placeholder={placeholder}
        readOnly={readOnly}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}
