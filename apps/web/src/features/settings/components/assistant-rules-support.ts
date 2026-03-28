import type { AssistantRuleProfile, AssistantRuleScope } from "@/lib/api/types";

export type AssistantRuleDraft = {
  content: string;
  enabled: boolean;
};

export function toAssistantRuleDraft(profile: AssistantRuleProfile): AssistantRuleDraft {
  return {
    enabled: profile.enabled,
    content: profile.content,
  };
}

export function isAssistantRuleDirty(
  draft: AssistantRuleDraft,
  profile: AssistantRuleProfile,
): boolean {
  return draft.enabled !== profile.enabled || draft.content !== profile.content;
}

export function buildAssistantRuleFormKey(profile: AssistantRuleProfile | undefined): string {
  if (!profile) {
    return "assistant-rules:empty";
  }
  return `${profile.scope}:${profile.updated_at ?? "none"}:${profile.enabled}:${profile.content}`;
}

export function buildAssistantRuleFieldId(scope: AssistantRuleScope): string {
  return `${scope}-assistant-rules`;
}
