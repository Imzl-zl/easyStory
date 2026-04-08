export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export type AuthLoginPayload = {
  username: string;
  password: string;
};

export type AuthRegisterPayload = AuthLoginPayload & {
  email?: string;
};

export type AuthToken = {
  access_token: string;
  token_type: "bearer";
  user_id: string;
  username: string;
};

export type TemplateNodeView = {
  id: string;
  node_order: number;
  node_id: string | null;
  node_name: string | null;
  node_type: string;
  skill_id: string | null;
  config: Record<string, JsonValue> | null;
  position_x: number | null;
  position_y: number | null;
  ui_config: Record<string, JsonValue> | null;
};

export type TemplateGuidedQuestion = {
  question: string;
  variable: string;
};

export type TemplateUpsertPayload = {
  name: string;
  description?: string | null;
  genre?: string | null;
  workflow_id: string;
  guided_questions: TemplateGuidedQuestion[];
};

export type TemplateSummary = {
  id: string;
  name: string;
  description: string | null;
  genre: string | null;
  workflow_id: string | null;
  is_builtin: boolean;
  node_count: number;
  created_at: string;
  updated_at: string;
};

export type TemplateDetail = TemplateSummary & {
  config: Record<string, JsonValue> | null;
  guided_questions: TemplateGuidedQuestion[];
  nodes: TemplateNodeView[];
};

export type CredentialOwnerType = "system" | "user" | "project";
export type CredentialApiDialect =
  | "openai_chat_completions"
  | "openai_responses"
  | "anthropic_messages"
  | "gemini_generate_content";
export type CredentialAuthStrategy = "bearer" | "x_api_key" | "x_goog_api_key" | "custom_header";
export type CredentialInteropProfile =
  | "responses_strict"
  | "responses_delta_first_terminal_empty_output"
  | "chat_compat_plain"
  | "chat_compat_reasoning_content"
  | "chat_compat_usage_extra_chunk";
export type CredentialRuntimeKind = "server-python" | "server-node" | "browser";
export type CredentialVerifyProbeKind =
  | "text_probe"
  | "tool_definition_probe"
  | "tool_call_probe"
  | "tool_continuation_probe";

export type CredentialView = {
  id: string;
  owner_type: CredentialOwnerType;
  owner_id: string | null;
  provider: string;
  api_dialect: CredentialApiDialect;
  display_name: string;
  masked_key: string;
  base_url: string | null;
  default_model: string | null;
  interop_profile?: CredentialInteropProfile | null;
  verified_probe_kind?: CredentialVerifyProbeKind | null;
  context_window_tokens: number | null;
  default_max_output_tokens: number | null;
  auth_strategy: CredentialAuthStrategy | null;
  api_key_header_name: string | null;
  extra_headers: Record<string, string> | null;
  user_agent_override: string | null;
  client_name: string | null;
  client_version: string | null;
  runtime_kind: CredentialRuntimeKind | null;
  is_active: boolean;
  last_verified_at: string | null;
};

export type CredentialCreatePayload = {
  owner_type: CredentialOwnerType;
  project_id?: string | null;
  provider: string;
  api_dialect: CredentialApiDialect;
  display_name: string;
  api_key: string;
  base_url?: string | null;
  default_model: string;
  interop_profile?: CredentialInteropProfile | null;
  context_window_tokens?: number | null;
  default_max_output_tokens?: number | null;
  auth_strategy?: CredentialAuthStrategy | null;
  api_key_header_name?: string | null;
  extra_headers?: Record<string, string> | null;
  user_agent_override?: string | null;
  client_name?: string | null;
  client_version?: string | null;
  runtime_kind?: CredentialRuntimeKind | null;
};

export type CredentialUpdatePayload = {
  api_dialect?: CredentialApiDialect | null;
  display_name?: string | null;
  api_key?: string | null;
  base_url?: string | null;
  default_model?: string | null;
  interop_profile?: CredentialInteropProfile | null;
  context_window_tokens?: number | null;
  default_max_output_tokens?: number | null;
  auth_strategy?: CredentialAuthStrategy | null;
  api_key_header_name?: string | null;
  extra_headers?: Record<string, string> | null;
  user_agent_override?: string | null;
  client_name?: string | null;
  client_version?: string | null;
  runtime_kind?: CredentialRuntimeKind | null;
};

export type CredentialVerifyResult = {
  credential_id: string;
  probe_kind: CredentialVerifyProbeKind;
  status: "verified";
  last_verified_at: string;
  message: string;
};
