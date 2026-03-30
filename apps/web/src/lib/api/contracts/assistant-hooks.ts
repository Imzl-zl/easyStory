import type { JsonValue } from "./base";

export type AssistantHookEvent = "before_assistant_response" | "after_assistant_response";
export type AssistantHookActionType = "agent" | "mcp";

export type AssistantAgentHookAction = {
  action_type: "agent";
  agent_id: string;
  input_mapping: Record<string, string>;
};

export type AssistantMcpHookAction = {
  action_type: "mcp";
  server_id: string;
  tool_name: string;
  arguments: Record<string, JsonValue>;
  input_mapping: Record<string, string>;
};

export type AssistantHookAction = AssistantAgentHookAction | AssistantMcpHookAction;

export type AssistantHookSummary = {
  id: string;
  file_name: string | null;
  name: string;
  description: string | null;
  enabled: boolean;
  event: AssistantHookEvent;
  action: AssistantHookAction;
  updated_at: string | null;
};

export type AssistantHookDetail = AssistantHookSummary;

export type AssistantHookPayload = {
  name: string;
  description?: string;
  enabled: boolean;
  event: AssistantHookEvent;
  action: AssistantHookAction;
};
