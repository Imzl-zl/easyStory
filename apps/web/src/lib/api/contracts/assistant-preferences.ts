export type OpenAIReasoningEffort = "none" | "minimal" | "low" | "medium" | "high" | "xhigh";
export type GeminiThinkingLevel = "minimal" | "low" | "medium" | "high";

export type AssistantPreferences = {
  default_provider: string | null;
  default_model_name: string | null;
  default_max_output_tokens: number | null;
  default_reasoning_effort: OpenAIReasoningEffort | null;
  default_thinking_level: GeminiThinkingLevel | null;
  default_thinking_budget: number | null;
};

export type AssistantPreferencesUpdatePayload = {
  default_provider?: string | null;
  default_model_name?: string | null;
  default_max_output_tokens?: number | null;
  default_reasoning_effort?: OpenAIReasoningEffort | null;
  default_thinking_level?: GeminiThinkingLevel | null;
  default_thinking_budget?: number | null;
};
