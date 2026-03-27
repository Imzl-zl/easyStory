import type {
  AgentConfigDetail,
  ConfigRegistryObject,
  HookActionType,
  HookConfigDetail,
  SkillConfigDetail,
} from "@/lib/api/types";
import type { JsonValue } from "@/lib/api/contracts/base";

export const AGENT_TYPE_OPTIONS = [
  { label: "writer", value: "writer" },
  { label: "reviewer", value: "reviewer" },
  { label: "checker", value: "checker" },
] as const;

export const HOOK_ACTION_TYPE_OPTIONS = [
  { label: "script", value: "script" },
  { label: "webhook", value: "webhook" },
  { label: "agent", value: "agent" },
  { label: "mcp", value: "mcp" },
] as const;

export const HOOK_EVENT_OPTIONS = [
  { label: "before_workflow_start", value: "before_workflow_start" },
  { label: "after_workflow_end", value: "after_workflow_end" },
  { label: "before_node_start", value: "before_node_start" },
  { label: "after_node_end", value: "after_node_end" },
  { label: "before_generate", value: "before_generate" },
  { label: "after_generate", value: "after_generate" },
  { label: "before_review", value: "before_review" },
  { label: "after_review", value: "after_review" },
  { label: "on_review_fail", value: "on_review_fail" },
  { label: "before_fix", value: "before_fix" },
  { label: "after_fix", value: "after_fix" },
  { label: "before_assistant_response", value: "before_assistant_response" },
  { label: "after_assistant_response", value: "after_assistant_response" },
  { label: "on_error", value: "on_error" },
] as const;

export const HOOK_NODE_TYPE_OPTIONS = [
  { label: "generate", value: "generate" },
  { label: "review", value: "review" },
  { label: "export", value: "export" },
] as const;

export const WEBHOOK_METHOD_OPTIONS = [
  { label: "POST", value: "POST" },
  { label: "PUT", value: "PUT" },
  { label: "PATCH", value: "PATCH" },
  { label: "GET", value: "GET" },
] as const;

export function formatCommaSeparatedList(values: string[]): string {
  return values.join(", ");
}

export function parseCommaSeparatedList(value: string): string[] {
  const seen = new Set<string>();
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => {
      if (!item || seen.has(item)) {
        return false;
      }
      seen.add(item);
      return true;
    });
}

export function validateJsonObject(parsed: unknown): {
  errorMessage: string | null;
  value: ConfigRegistryObject | null;
} {
  if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
    return { errorMessage: "这里必须是 JSON 对象。", value: null };
  }
  return { errorMessage: null, value: parsed as ConfigRegistryObject };
}

export function validateNullableJsonObject(parsed: unknown): {
  errorMessage: string | null;
  value: ConfigRegistryObject | null;
} {
  if (parsed === null) {
    return { errorMessage: null, value: null };
  }
  return validateJsonObject(parsed);
}

export function validateJsonValue(parsed: unknown): {
  errorMessage: string | null;
  value: JsonValue;
} {
  return { errorMessage: null, value: parsed as JsonValue };
}

export function validateStringMap(parsed: unknown): {
  errorMessage: string | null;
  value: Record<string, string> | null;
} {
  const result = validateJsonObject(parsed);
  if (result.errorMessage || result.value === null) {
    return { errorMessage: result.errorMessage, value: null };
  }
  const entries = Object.entries(result.value);
  if (entries.some(([, value]) => typeof value !== "string")) {
    return { errorMessage: "这里必须是 string:string 的 JSON 对象。", value: null };
  }
  return { errorMessage: null, value: result.value as Record<string, string> };
}

export function buildDefaultModelConfig(): ConfigRegistryObject {
  return {
    max_tokens: 4000,
    name: "",
    provider: "",
    required_capabilities: [],
    temperature: 0.7,
    top_p: null,
  };
}

export function normalizeModelConfig(value: ConfigRegistryObject | null): ConfigRegistryObject | null {
  if (value === null) {
    return null;
  }
  return { ...buildDefaultModelConfig(), ...value };
}

export function patchModelConfig(
  current: ConfigRegistryObject | null,
  patch: Partial<ConfigRegistryObject>,
): ConfigRegistryObject {
  return {
    ...buildDefaultModelConfig(),
    ...removeUndefinedFields(current ?? {}),
    ...removeUndefinedFields(patch),
  };
}

export function isHookNodeEvent(event: string): boolean {
  return (
    event === "before_node_start" ||
    event === "after_node_end" ||
    event === "before_generate" ||
    event === "after_generate" ||
    event === "before_review" ||
    event === "after_review" ||
    event === "on_review_fail" ||
    event === "before_fix" ||
    event === "after_fix" ||
    event === "on_error"
  );
}

export function buildDefaultHookActionConfig(actionType: HookActionType): ConfigRegistryObject {
  if (actionType === "script") {
    return { function: "", module: "", params: {} };
  }
  if (actionType === "webhook") {
    return { body: {}, headers: {}, method: "POST", url: "" };
  }
  if (actionType === "agent") {
    return { agent_id: "", input_mapping: {} };
  }
  return { arguments: {}, input_mapping: {}, server_id: "", tool_name: "" };
}

export function sanitizeSkillDraft(draft: SkillConfigDetail): SkillConfigDetail {
  return {
    ...draft,
    inputs: draft.inputs ?? {},
    outputs: draft.outputs ?? {},
    tags: draft.tags ?? [],
    variables: draft.variables ?? {},
  };
}

export function sanitizeAgentDraft(draft: AgentConfigDetail): AgentConfigDetail {
  return {
    ...draft,
    mcp_servers: draft.mcp_servers ?? [],
    output_schema: draft.agent_type === "reviewer" ? null : draft.output_schema,
    skill_ids: draft.skill_ids ?? [],
    tags: draft.tags ?? [],
  };
}

export function sanitizeHookDraft(draft: HookConfigDetail): HookConfigDetail {
  const event = draft.trigger.event;
  return {
    ...draft,
    action: {
      ...draft.action,
      config: draft.action.config ?? buildDefaultHookActionConfig(draft.action.action_type),
    },
    retry: draft.retry,
    trigger: {
      ...draft.trigger,
      node_types: isHookNodeEvent(event) ? draft.trigger.node_types ?? [] : [],
    },
  };
}

function removeUndefinedFields<T extends Record<string, JsonValue | undefined>>(value: T): Record<string, JsonValue> {
  return Object.fromEntries(
    Object.entries(value).filter(([, item]) => item !== undefined),
  ) as Record<string, JsonValue>;
}
