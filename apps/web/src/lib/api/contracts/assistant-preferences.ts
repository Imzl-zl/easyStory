export type AssistantPreferences = {
  default_provider: string | null;
  default_model_name: string | null;
  default_max_output_tokens: number;
};

export type AssistantPreferencesUpdatePayload = {
  default_provider?: string | null;
  default_model_name?: string | null;
  default_max_output_tokens?: number | null;
};
