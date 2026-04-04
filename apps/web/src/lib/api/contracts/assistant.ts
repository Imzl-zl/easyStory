export type AssistantMessageRole = "user" | "assistant";

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

export type AssistantContinuationAnchor = {
  previous_run_id: string;
  messages_digest?: string | null;
};

export type AssistantActiveBufferState = {
  dirty: boolean;
  base_version?: string | null;
  buffer_hash?: string | null;
  source?: string | null;
};

export type AssistantDocumentContext = {
  active_path?: string | null;
  active_document_ref?: string | null;
  active_binding_version?: string | null;
  selected_paths?: string[];
  selected_document_refs?: string[];
  active_buffer_state?: AssistantActiveBufferState | null;
  catalog_version?: string | null;
};

export type AssistantOutputItem = {
  item_type: "text" | "tool_call" | "tool_result" | "reasoning" | "refusal";
  item_id: string;
  status?: string | null;
  provider_ref?: string | null;
  call_id?: string | null;
  payload?: unknown;
};

export type AssistantOutputMeta = {
  finish_reason?: string | null;
  input_tokens?: number | null;
  output_tokens?: number | null;
  total_tokens?: number | null;
};

export type AssistantTurnPayload = {
  conversation_id: string;
  client_turn_id: string;
  agent_id?: string;
  skill_id?: string;
  continuation_anchor?: AssistantContinuationAnchor | null;
  stream?: boolean;
  hook_ids?: string[];
  project_id?: string | null;
  messages: AssistantMessage[];
  document_context?: AssistantDocumentContext | null;
  requested_write_scope?: "disabled" | "turn";
  requested_write_targets?: string[] | null;
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
  run_id: string;
  conversation_id: string;
  client_turn_id: string;
  agent_id: string | null;
  skill_id: string | null;
  provider: string;
  model_name: string;
  content: string;
  output_items: AssistantOutputItem[];
  output_meta: AssistantOutputMeta;
  hook_results: AssistantHookResult[];
  mcp_servers: string[];
  input_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
};
