export type AssistantRuleScope = "user" | "project";

export type AssistantRuleProfile = {
  scope: AssistantRuleScope;
  enabled: boolean;
  content: string;
  updated_at: string | null;
};

export type AssistantRuleUpdatePayload = {
  enabled: boolean;
  content: string;
};
