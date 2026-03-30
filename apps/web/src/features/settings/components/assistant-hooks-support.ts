"use client";

import type {
  AssistantHookAction,
  AssistantHookActionType,
  AssistantHookDetail,
  AssistantHookEvent,
  AssistantHookPayload,
} from "@/lib/api/types";
import type { JsonValue } from "@/lib/api/contracts/base";

import {
  assertYamlKeys,
  parseAssistantYamlDocument,
  readOptionalYamlArray,
  readOptionalYamlBoolean,
  readOptionalYamlInteger,
  readOptionalYamlObject,
  readOptionalYamlString,
  readRequiredYamlObject,
  readRequiredYamlString,
  validateJsonRecord,
  validateStringRecord,
  type AssistantYamlObject,
} from "./assistant-yaml-document-support";

export const ASSISTANT_HOOK_FILE_LABEL = "HOOK.yaml";
export const ASSISTANT_HOOK_FIXED_AUTHOR = "user";
export const ASSISTANT_HOOK_FIXED_PRIORITY = 10;
export const ASSISTANT_HOOK_FIXED_TIMEOUT = 30;
export const ASSISTANT_HOOK_EVENT_OPTIONS = [
  { label: "回复前先处理", value: "before_assistant_response" },
  { label: "回复后自动处理", value: "after_assistant_response" },
] as const satisfies ReadonlyArray<{ label: string; value: AssistantHookEvent }>;
export const ASSISTANT_HOOK_ACTION_TYPE_OPTIONS = [
  { label: "Agent", value: "agent" },
  { label: "MCP", value: "mcp" },
] as const satisfies ReadonlyArray<{ label: string; value: AssistantHookActionType }>;

export type AssistantHookDraft = {
  actionType: AssistantHookActionType;
  agentId: string;
  arguments: Record<string, JsonValue>;
  description: string;
  enabled: boolean;
  event: AssistantHookEvent;
  inputMapping: Record<string, string>;
  name: string;
  serverId: string;
  toolName: string;
};

export function createEmptyAssistantHookDraft(): AssistantHookDraft {
  return {
    actionType: "agent",
    agentId: "",
    arguments: {},
    description: "",
    enabled: true,
    event: "after_assistant_response",
    inputMapping: {},
    name: "",
    serverId: "",
    toolName: "",
  };
}

export function toAssistantHookDraft(detail: AssistantHookDetail): AssistantHookDraft {
  if (detail.action.action_type === "agent") {
    return {
      actionType: "agent",
      agentId: detail.action.agent_id,
      arguments: {},
      description: detail.description ?? "",
      enabled: detail.enabled,
      event: detail.event,
      inputMapping: detail.action.input_mapping,
      name: detail.name,
      serverId: "",
      toolName: "",
    };
  }
  return {
    actionType: "mcp",
    agentId: "",
    arguments: detail.action.arguments,
    description: detail.description ?? "",
    enabled: detail.enabled,
    event: detail.event,
    inputMapping: detail.action.input_mapping,
    name: detail.name,
    serverId: detail.action.server_id,
    toolName: detail.action.tool_name,
  };
}

export function buildAssistantHookPayload(draft: AssistantHookDraft): AssistantHookPayload {
  return {
    action: buildAssistantHookActionPayload(draft),
    description: draft.description.trim(),
    enabled: draft.enabled,
    event: draft.event,
    name: draft.name.trim(),
  };
}

export function buildAssistantHookDocumentPreview(
  draft: AssistantHookDraft,
  options: { hookId?: string | null } = {},
) {
  const lines = ["hook:"];
  if (options.hookId) {
    lines.push(`  id: ${options.hookId}`);
  }
  lines.push(`  name: ${formatPreviewText(draft.name.trim() || "未命名 Hook")}`);
  lines.push(`  enabled: ${draft.enabled ? "true" : "false"}`);
  if (draft.description.trim()) {
    lines.push(`  description: ${formatPreviewText(draft.description.trim())}`);
  }
  lines.push(`  author: ${ASSISTANT_HOOK_FIXED_AUTHOR}`);
  lines.push("  trigger:");
  lines.push(`    event: ${draft.event}`);
  lines.push("    node_types: []");
  lines.push("  action:");
  lines.push(`    type: ${draft.actionType}`);
  lines.push("    config:");
  if (draft.actionType === "agent") {
    lines.push(`      agent_id: ${draft.agentId.trim() || "agent.user.example"}`);
    lines.push(`      input_mapping: ${formatPreviewObject(draft.inputMapping)}`);
  } else {
    lines.push(`      server_id: ${draft.serverId.trim() || "mcp.user.example"}`);
    lines.push(`      tool_name: ${formatPreviewText(draft.toolName.trim() || "tool_name")}`);
      lines.push(`      arguments: ${formatPreviewObject(draft.arguments)}`);
      lines.push(`      input_mapping: ${formatPreviewObject(draft.inputMapping)}`);
  }
  lines.push(`  priority: ${ASSISTANT_HOOK_FIXED_PRIORITY}`);
  lines.push(`  timeout: ${ASSISTANT_HOOK_FIXED_TIMEOUT}`);
  return lines.join("\n");
}

export function parseAssistantHookDocument(
  source: string,
  expectedId?: string | null,
): AssistantHookDraft {
  const document = parseAssistantYamlDocument(source, "hook");
  assertYamlKeys(
    document,
    ["action", "author", "description", "enabled", "id", "name", "priority", "timeout", "trigger"],
    "HOOK.yaml",
  );
  validateExpectedId(document, expectedId);
  validateFixedHookFields(document);

  const trigger = readRequiredYamlObject(document, "trigger", "HOOK.yaml trigger");
  assertYamlKeys(trigger, ["event", "node_types"], "HOOK.yaml trigger");
  const action = readRequiredYamlObject(document, "action", "HOOK.yaml action");
  assertYamlKeys(action, ["config", "type"], "HOOK.yaml action");

  const event = parseHookEvent(readRequiredYamlString(trigger, "event", "HOOK.yaml trigger.event"));
  const actionType = parseHookActionType(
    readRequiredYamlString(action, "type", "HOOK.yaml action.type"),
  );
  const config = readRequiredYamlObject(action, "config", "HOOK.yaml action.config");

  return {
    actionType,
    agentId: resolveHookAgentId(config, actionType),
    arguments: resolveHookArguments(config, actionType),
    description: readOptionalYamlString(document, "description", "HOOK.yaml description") ?? "",
    enabled: readOptionalYamlBoolean(document, "enabled", "HOOK.yaml enabled") ?? true,
    event,
    inputMapping: resolveHookInputMapping(config, actionType),
    name: readRequiredYamlString(document, "name", "HOOK.yaml name"),
    serverId: resolveHookServerId(config, actionType),
    toolName: resolveHookToolName(config, actionType),
  };
}

export function isAssistantHookDirty(
  draft: AssistantHookDraft,
  detail: AssistantHookDetail | null,
) {
  if (detail === null) {
    return hasDraftContent(draft);
  }
  return JSON.stringify(draft) !== JSON.stringify(toAssistantHookDraft(detail));
}

export function buildAssistantHookListDescription(
  detail: Pick<AssistantHookDetail, "action" | "description" | "enabled" | "event">,
  options: { agentLabel?: string | null; mcpLabel?: string | null } = {},
) {
  if (!detail.enabled) {
    return "已停用";
  }
  if (detail.description?.trim()) {
    return detail.description.trim();
  }
  return `${resolveAssistantHookEventLabel(detail.event)} · ${resolveAssistantHookTargetLabel(detail.action, options)}`;
}

export function resolveAssistantHookEventLabel(event: AssistantHookEvent) {
  return event === "before_assistant_response" ? "回复前先处理" : "回复后自动处理";
}

export function resolveAssistantHookActionLabel(actionType: AssistantHookActionType) {
  return actionType === "agent" ? "Agent" : "MCP";
}

export function resolveAssistantHookTargetLabel(
  action: AssistantHookAction,
  options: { agentLabel?: string | null; mcpLabel?: string | null } = {},
) {
  if (action.action_type === "agent") {
    return options.agentLabel ?? action.agent_id;
  }
  const serverLabel = options.mcpLabel ?? action.server_id;
  return `${serverLabel} · ${action.tool_name}`;
}

export function validateAssistantHookJsonObject(parsed: unknown): {
  errorMessage: string | null;
  value: Record<string, JsonValue> | null;
} {
  if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
    return { errorMessage: "需要填写对象格式的配置。", value: null };
  }
  return { errorMessage: null, value: parsed as Record<string, JsonValue> };
}

export function validateAssistantHookStringMap(parsed: unknown): {
  errorMessage: string | null;
  value: Record<string, string> | null;
} {
  const result = validateAssistantHookJsonObject(parsed);
  if (result.errorMessage || result.value === null) {
    return { errorMessage: result.errorMessage, value: null };
  }
  const entries = Object.entries(result.value);
  if (entries.some(([, value]) => typeof value !== "string")) {
    return { errorMessage: "需要填写“名称: 内容”的对象格式。", value: null };
  }
  return { errorMessage: null, value: result.value as Record<string, string> };
}

function buildAssistantHookActionPayload(draft: AssistantHookDraft): AssistantHookAction {
  if (draft.actionType === "agent") {
    return {
      action_type: "agent",
      agent_id: draft.agentId.trim(),
      input_mapping: normalizeStringMap(draft.inputMapping),
    };
  }
  return {
    action_type: "mcp",
    arguments: { ...draft.arguments },
    input_mapping: normalizeStringMap(draft.inputMapping),
    server_id: draft.serverId.trim(),
    tool_name: draft.toolName.trim(),
  };
}

function hasDraftContent(draft: AssistantHookDraft) {
  return Boolean(
    draft.name.trim()
      || draft.description.trim()
      || draft.agentId.trim()
      || draft.serverId.trim()
      || draft.toolName.trim()
      || Object.keys(draft.arguments).length > 0
      || Object.keys(draft.inputMapping).length > 0
      || draft.actionType !== "agent"
      || draft.event !== "after_assistant_response",
  ) || !draft.enabled;
}

function normalizeStringMap(value: Record<string, string>) {
  return Object.fromEntries(
    Object.entries(value)
      .map(([key, item]) => [key.trim(), item.trim()])
      .filter(([key, item]) => key && item),
  );
}

function formatPreviewText(value: string) {
  return JSON.stringify(value);
}

function formatPreviewObject(value: Record<string, JsonValue> | Record<string, string>) {
  return JSON.stringify(value);
}

function parseHookActionType(value: string): AssistantHookActionType {
  if (value !== "agent" && value !== "mcp") {
    throw new Error("HOOK.yaml action.type 只支持 agent 或 mcp。");
  }
  return value;
}

function parseHookEvent(value: string): AssistantHookEvent {
  if (value !== "before_assistant_response" && value !== "after_assistant_response") {
    throw new Error("HOOK.yaml trigger.event 只支持 before_assistant_response 或 after_assistant_response。");
  }
  return value;
}

function resolveHookAgentId(config: AssistantYamlObject, actionType: AssistantHookActionType) {
  if (actionType !== "agent") {
    return "";
  }
  assertYamlKeys(config, ["agent_id", "input_mapping"], "HOOK.yaml action.config");
  return readRequiredYamlString(config, "agent_id", "HOOK.yaml action.config.agent_id");
}

function resolveHookArguments(config: AssistantYamlObject, actionType: AssistantHookActionType) {
  if (actionType !== "mcp") {
    return {};
  }
  assertYamlKeys(config, ["arguments", "input_mapping", "server_id", "tool_name"], "HOOK.yaml action.config");
  return validateJsonRecord(
    readOptionalYamlObject(config, "arguments", "HOOK.yaml action.config.arguments") ?? {},
    "HOOK.yaml action.config.arguments",
  );
}

function resolveHookInputMapping(config: AssistantYamlObject, actionType: AssistantHookActionType) {
  if (actionType === "agent") {
    return validateStringRecord(
      readOptionalYamlObject(config, "input_mapping", "HOOK.yaml action.config.input_mapping") ?? {},
      "HOOK.yaml action.config.input_mapping",
    );
  }
  return validateStringRecord(
    readOptionalYamlObject(config, "input_mapping", "HOOK.yaml action.config.input_mapping") ?? {},
    "HOOK.yaml action.config.input_mapping",
  );
}

function resolveHookServerId(config: AssistantYamlObject, actionType: AssistantHookActionType) {
  if (actionType !== "mcp") {
    return "";
  }
  return readRequiredYamlString(config, "server_id", "HOOK.yaml action.config.server_id");
}

function resolveHookToolName(config: AssistantYamlObject, actionType: AssistantHookActionType) {
  if (actionType !== "mcp") {
    return "";
  }
  return readRequiredYamlString(config, "tool_name", "HOOK.yaml action.config.tool_name");
}

function validateExpectedId(document: AssistantYamlObject, expectedId: string | null | undefined) {
  const parsedId = readOptionalYamlString(document, "id", "HOOK.yaml id");
  if (expectedId && parsedId && parsedId !== expectedId) {
    throw new Error("Hook 的 id 由系统维护，不能在这里修改。");
  }
}

function validateFixedHookFields(document: AssistantYamlObject) {
  const author = readOptionalYamlString(document, "author", "HOOK.yaml author");
  if (author !== null && author !== ASSISTANT_HOOK_FIXED_AUTHOR) {
    throw new Error(`当前只支持 author: ${ASSISTANT_HOOK_FIXED_AUTHOR}。`);
  }
  const priority = readOptionalYamlInteger(document, "priority", "HOOK.yaml priority");
  if (priority !== null && priority !== ASSISTANT_HOOK_FIXED_PRIORITY) {
    throw new Error(`当前只支持 priority: ${ASSISTANT_HOOK_FIXED_PRIORITY}。`);
  }
  const timeout = readOptionalYamlInteger(document, "timeout", "HOOK.yaml timeout");
  if (timeout !== null && timeout !== ASSISTANT_HOOK_FIXED_TIMEOUT) {
    throw new Error(`当前只支持 timeout: ${ASSISTANT_HOOK_FIXED_TIMEOUT}。`);
  }
  const trigger = readOptionalYamlObject(document, "trigger", "HOOK.yaml trigger");
  const nodeTypes = readOptionalYamlArray(trigger ?? {}, "node_types", "HOOK.yaml trigger.node_types");
  if (nodeTypes !== null && nodeTypes.length > 0) {
    throw new Error("当前 assistant Hook 不支持填写 trigger.node_types。");
  }
}
