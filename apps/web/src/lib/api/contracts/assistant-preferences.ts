export type AssistantPreferences = {
  default_provider: string | null;
  default_model_name: string | null;
};

export type AssistantPreferencesUpdatePayload = {
  default_provider?: string | null;
  default_model_name?: string | null;
};
