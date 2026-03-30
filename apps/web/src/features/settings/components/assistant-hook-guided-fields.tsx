"use client";

import { JsonTextAreaField } from "@/features/config-registry/components/config-registry-json-field";

import {
  AssistantSelectField,
  AssistantTextareaField,
  AssistantTextField,
  AssistantToggleField,
} from "./assistant-editor-primitives";
import {
  ASSISTANT_HOOK_ACTION_TYPE_OPTIONS,
  ASSISTANT_HOOK_EVENT_OPTIONS,
  type AssistantHookDraft,
  validateAssistantHookJsonObject,
  validateAssistantHookStringMap,
} from "./assistant-hooks-support";

export type AssistantHookFieldErrorKey = "agentInputMapping" | "arguments" | "inputMapping";

type HookOption = { label: string; value: string; description?: string };

type HookGuidedFormPanelProps = {
  agentErrorMessage?: string | null;
  agentOptions: HookOption[];
  draft: AssistantHookDraft;
  mcpErrorMessage?: string | null;
  mcpOptions: HookOption[];
  onChange: (draft: AssistantHookDraft) => void;
  onFieldErrorChange: (field: AssistantHookFieldErrorKey, message: string | null) => void;
};

export function HookGuidedFormPanel({
  agentErrorMessage,
  agentOptions,
  draft,
  mcpErrorMessage,
  mcpOptions,
  onChange,
  onFieldErrorChange,
}: Readonly<HookGuidedFormPanelProps>) {
  return (
    <div className="space-y-4">
      <div className="rounded-2xl bg-[rgba(58,124,165,0.07)] px-4 py-3 text-[12px] leading-6 text-[var(--text-secondary)]">
        Hook 会在回复前后自动多做一步。你可以让它调用一个 Agent，也可以直接连接一个 MCP 工具。
      </div>
      <AssistantTextField
        label="名称"
        maxLength={80}
        placeholder="例如：回复后自动整理"
        value={draft.name}
        onChange={(value) => onChange({ ...draft, name: value })}
      />
      <AssistantTextareaField
        label="一句说明"
        maxLength={240}
        placeholder="例如：每次回复后自动提炼一句重点。"
        value={draft.description}
        onChange={(value) => onChange({ ...draft, description: value })}
      />
      <AssistantToggleField
        checked={draft.enabled}
        description="关闭后不会在聊天里执行，但文件会保留。"
        label="启用"
        onChange={(checked) => onChange({ ...draft, enabled: checked })}
      />
      <AssistantSelectField
        label="执行时机"
        options={ASSISTANT_HOOK_EVENT_OPTIONS}
        value={draft.event}
        onChange={(value) => onChange({ ...draft, event: value as AssistantHookDraft["event"] })}
      />
      <AssistantSelectField
        label="动作类型"
        options={ASSISTANT_HOOK_ACTION_TYPE_OPTIONS}
        value={draft.actionType}
        onChange={(value) =>
          onChange({ ...draft, actionType: value as AssistantHookDraft["actionType"] })
        }
      />
      {draft.actionType === "agent" ? (
        <HookAgentFields
          agentErrorMessage={agentErrorMessage}
          agentOptions={agentOptions}
          draft={draft}
          onChange={onChange}
          onFieldErrorChange={onFieldErrorChange}
        />
      ) : (
        <HookMcpFields
          draft={draft}
          mcpErrorMessage={mcpErrorMessage}
          mcpOptions={mcpOptions}
          onChange={onChange}
          onFieldErrorChange={onFieldErrorChange}
        />
      )}
    </div>
  );
}

function HookAgentFields({
  agentErrorMessage,
  agentOptions,
  draft,
  onChange,
  onFieldErrorChange,
}: Readonly<{
  agentErrorMessage?: string | null;
  agentOptions: HookOption[];
  draft: AssistantHookDraft;
  onChange: (draft: AssistantHookDraft) => void;
  onFieldErrorChange: (field: AssistantHookFieldErrorKey, message: string | null) => void;
}>) {
  return (
    <>
      <AssistantSelectField
        description={agentErrorMessage ?? "这个 Agent 会在指定时机自动执行。"}
        label="选择 Agent"
        options={[{ label: "请选择 Agent", value: "" }, ...agentOptions]}
        tone={agentErrorMessage ? "danger" : "default"}
        value={draft.agentId}
        onChange={(value) => onChange({ ...draft, agentId: value })}
      />
      <JsonTextAreaField
        emptyValue={{}}
        helpText="需要手动映射时再填写；留空就按默认方式执行。"
        label="输入映射"
        parseValue={validateAssistantHookStringMap}
        value={draft.inputMapping}
        onChange={(value) => onChange({ ...draft, inputMapping: value ?? {} })}
        onErrorChange={(message) => onFieldErrorChange("agentInputMapping", message)}
      />
    </>
  );
}

function HookMcpFields({
  draft,
  mcpErrorMessage,
  mcpOptions,
  onChange,
  onFieldErrorChange,
}: Readonly<{
  draft: AssistantHookDraft;
  mcpErrorMessage?: string | null;
  mcpOptions: HookOption[];
  onChange: (draft: AssistantHookDraft) => void;
  onFieldErrorChange: (field: AssistantHookFieldErrorKey, message: string | null) => void;
}>) {
  return (
    <>
      <AssistantSelectField
        description={mcpErrorMessage ?? "先选一个你自己的 MCP，再填写要调用的工具名称。"}
        label="选择 MCP"
        options={[{ label: "请选择 MCP", value: "" }, ...mcpOptions]}
        tone={mcpErrorMessage ? "danger" : "default"}
        value={draft.serverId}
        onChange={(value) => onChange({ ...draft, serverId: value })}
      />
      <AssistantTextField
        label="工具名称"
        maxLength={120}
        placeholder="例如：search_news"
        value={draft.toolName}
        onChange={(value) => onChange({ ...draft, toolName: value })}
      />
      <JsonTextAreaField
        emptyValue={{}}
        helpText="这里填写固定参数；需要从当前聊天里取值时，用下面的输入映射。"
        label="调用参数"
        parseValue={validateAssistantHookJsonObject}
        value={draft.arguments}
        onChange={(value) => onChange({ ...draft, arguments: value ?? {} })}
        onErrorChange={(message) => onFieldErrorChange("arguments", message)}
      />
      <JsonTextAreaField
        emptyValue={{}}
        helpText='例如：{ "query": "request.user_input" }'
        label="输入映射"
        parseValue={validateAssistantHookStringMap}
        value={draft.inputMapping}
        onChange={(value) => onChange({ ...draft, inputMapping: value ?? {} })}
        onErrorChange={(message) => onFieldErrorChange("inputMapping", message)}
      />
    </>
  );
}
