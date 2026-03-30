export type AssistantSkillSummary = {
  id: string;
  name: string;
  description: string | null;
  enabled: boolean;
  updated_at: string | null;
};

export type AssistantSkillDetail = AssistantSkillSummary & {
  content: string;
  default_provider: string | null;
  default_model_name: string | null;
  default_max_output_tokens: number | null;
};

export type AssistantSkillPayload = {
  name: string;
  description?: string;
  enabled: boolean;
  content: string;
  default_provider?: string | null;
  default_model_name?: string | null;
  default_max_output_tokens?: number | null;
};
