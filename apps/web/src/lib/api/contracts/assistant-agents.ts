export type AssistantAgentSummary = {
  id: string;
  name: string;
  description: string | null;
  enabled: boolean;
  skill_id: string;
  updated_at: string | null;
};

export type AssistantAgentDetail = AssistantAgentSummary & {
  system_prompt: string;
  default_provider: string | null;
  default_model_name: string | null;
  default_max_output_tokens: number | null;
};

export type AssistantAgentPayload = {
  name: string;
  description?: string;
  enabled: boolean;
  skill_id: string;
  system_prompt: string;
  default_provider?: string | null;
  default_model_name?: string | null;
  default_max_output_tokens?: number | null;
};
