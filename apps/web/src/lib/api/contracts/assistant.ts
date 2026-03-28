export type AssistantMessageRole = "system" | "user" | "assistant";

export type AssistantMessage = {
  role: AssistantMessageRole;
  content: string;
};

export type AssistantModelConfig = {
  provider?: string | null;
  name?: string | null;
  required_capabilities?: string[];
  temperature?: number;
  max_tokens?: number;
  top_p?: number | null;
  frequency_penalty?: number | null;
  presence_penalty?: number | null;
  stop?: string[] | null;
};

export type AssistantTurnPayload = {
  agent_id?: string;
  skill_id?: string;
  stream?: boolean;
  hook_ids?: string[];
  project_id?: string | null;
  messages: AssistantMessage[];
  input_data?: Record<string, unknown>;
  model?: AssistantModelConfig | null;
};

export type AssistantHookResult = {
  event: string;
  hook_id: string;
  action_type: string;
  result: unknown;
};

export type AssistantTurnResult = {
  agent_id: string | null;
  skill_id: string;
  provider: string;
  model_name: string;
  content: string;
  hook_results: AssistantHookResult[];
  mcp_servers: string[];
  input_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
};
