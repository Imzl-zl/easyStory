import type { JsonValue } from "./base";

export type ConfigRegistryType = "skills" | "agents" | "hooks" | "workflows";
export type ConfigRegistryObject = Record<string, JsonValue>;
export type AgentType = "writer" | "reviewer" | "checker";
export type HookActionType = "script" | "webhook" | "agent";
export type WorkflowMode = "manual" | "auto";
export type WorkflowNodeType = "generate" | "review" | "export" | "custom";

export type ConfigRegistryModelReference = {
  provider: string | null;
  name: string | null;
  required_capabilities: string[];
  temperature: number;
  max_tokens: number;
};

export type ConfigRegistrySummaryBase = {
  author: string | null;
  description: string | null;
  id: string;
  name: string;
  version: string;
};

export type ConfigRegistryDetailBase = ConfigRegistrySummaryBase;

export type SkillConfigSummary = ConfigRegistrySummaryBase & {
  category: string;
  input_keys: string[];
  model: ConfigRegistryModelReference | null;
  output_keys: string[];
  tags: string[];
};

export type SkillConfigDetail = ConfigRegistryDetailBase & {
  category: string;
  inputs: ConfigRegistryObject;
  model: ConfigRegistryObject | null;
  outputs: ConfigRegistryObject;
  prompt: string;
  tags: string[];
  variables: ConfigRegistryObject;
};

export type AgentConfigSummary = ConfigRegistrySummaryBase & {
  agent_type: AgentType;
  mcp_servers: string[];
  model: ConfigRegistryModelReference | null;
  output_schema_keys: string[];
  skill_ids: string[];
  tags: string[];
};

export type AgentConfigDetail = ConfigRegistryDetailBase & {
  agent_type: AgentType;
  mcp_servers: string[];
  model: ConfigRegistryObject | null;
  output_schema: ConfigRegistryObject | null;
  skill_ids: string[];
  system_prompt: string;
  tags: string[];
};

export type HookConfigSummary = ConfigRegistrySummaryBase & {
  action_type: HookActionType;
  enabled: boolean;
  has_condition: boolean;
  priority: number;
  retry_enabled: boolean;
  timeout: number;
  trigger_event: string;
  trigger_node_types: string[];
};

export type HookConfigDetail = ConfigRegistryDetailBase & {
  action: {
    action_type: HookActionType;
    config: ConfigRegistryObject;
  };
  condition: {
    field: string;
    operator: string;
    value: string | number | boolean;
  } | null;
  enabled: boolean;
  priority: number;
  retry: {
    delay: number;
    max_attempts: number;
  } | null;
  timeout: number;
  trigger: {
    event: string;
    node_types: string[];
  };
};

export type ConfigRegistryWorkflowNodeSummary = {
  auto_fix: boolean | null;
  auto_proceed: boolean | null;
  auto_review: boolean | null;
  context_injection_types: string[];
  depends_on: string[];
  fix_skill_id: string | null;
  formats: string[];
  hook_ids: string[];
  hook_stages: string[];
  id: string;
  loop_enabled: boolean;
  name: string;
  node_type: WorkflowNodeType;
  reviewer_ids: string[];
  skill_id: string | null;
};

export type WorkflowConfigSummary = ConfigRegistrySummaryBase & {
  default_fix_skill: string | null;
  default_inject_types: string[];
  mode: WorkflowMode;
  model: ConfigRegistryModelReference | null;
  node_count: number;
  nodes: ConfigRegistryWorkflowNodeSummary[];
  tags: string[];
};

export type WorkflowConfigDetail = ConfigRegistryDetailBase & {
  budget: ConfigRegistryObject;
  changelog: JsonValue[];
  context_injection: ConfigRegistryObject | null;
  mode: WorkflowMode;
  model: ConfigRegistryObject | null;
  model_fallback: ConfigRegistryObject;
  nodes: ConfigRegistryObject[];
  retry: ConfigRegistryObject;
  safety: ConfigRegistryObject;
  settings: ConfigRegistryObject;
  tags: string[];
};

export type ConfigRegistrySummary =
  | SkillConfigSummary
  | AgentConfigSummary
  | HookConfigSummary
  | WorkflowConfigSummary;

export type ConfigRegistryDetail =
  | SkillConfigDetail
  | AgentConfigDetail
  | HookConfigDetail
  | WorkflowConfigDetail;
