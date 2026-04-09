import type {
  AssistantPreferences,
  CredentialView,
} from "@/lib/api/types";
import {
  sanitizeAssistantOutputTokenInput,
} from "@/features/shared/assistant/assistant-output-token-support";
import type { AssistantReasoningControl } from "@/features/shared/assistant/assistant-reasoning-support";
import {
  buildAssistantReasoningShapeError,
  buildAssistantReasoningPayload,
  normalizeAssistantReasoningDraft,
  parseAssistantThinkingBudgetDraft,
} from "@/features/shared/assistant/assistant-reasoning-support";

export type AssistantPreferencesScope = "user" | "project";

export type AssistantPreferencesDraft = {
  defaultModelName: string;
  defaultMaxOutputTokens: string;
  defaultProvider: string;
  defaultReasoningEffort: string;
  defaultThinkingBudget: string;
  defaultThinkingLevel: string;
};

export type AssistantProviderOption = {
  apiDialect?: string | null;
  defaultModel?: string;
  description?: string;
  label: string;
  value: string;
};

const FOLLOW_SYSTEM_PROVIDER_OPTION: AssistantProviderOption = {
  description: "不固定到某条连接，聊天时按系统默认方式处理。",
  label: "跟随系统默认",
  value: "",
};

const FOLLOW_USER_PROVIDER_OPTION: AssistantProviderOption = {
  description: "不单独指定这个项目的连接，继续跟随个人 AI 偏好。",
  label: "跟随个人 AI 偏好",
  value: "",
};

export function toAssistantPreferencesDraft(
  preferences: AssistantPreferences,
): AssistantPreferencesDraft {
  return {
    defaultModelName: preferences.default_model_name ?? "",
    defaultMaxOutputTokens: toAssistantPreferencesTokenDraft(preferences.default_max_output_tokens),
    defaultProvider: preferences.default_provider ?? "",
    defaultReasoningEffort: preferences.default_reasoning_effort ?? "",
    defaultThinkingBudget: preferences.default_thinking_budget === null
      ? ""
      : String(preferences.default_thinking_budget),
    defaultThinkingLevel: preferences.default_thinking_level ?? "",
  };
}

export function normalizeAssistantPreferencesDraft(
  draft: AssistantPreferencesDraft,
  reasoningControl: AssistantReasoningControl,
): AssistantPreferencesDraft {
  const reasoningDraft = {
    reasoningEffort: draft.defaultReasoningEffort,
    thinkingBudget: draft.defaultThinkingBudget,
    thinkingLevel: draft.defaultThinkingLevel,
  };
  if (buildAssistantReasoningShapeError(reasoningDraft)) {
    return draft;
  }
  const normalizedReasoning = normalizeAssistantReasoningDraft(
    reasoningDraft,
    reasoningControl,
  );
  return {
    ...draft,
    defaultReasoningEffort: normalizedReasoning.reasoningEffort,
    defaultThinkingBudget: normalizedReasoning.thinkingBudget,
    defaultThinkingLevel: normalizedReasoning.thinkingLevel,
  };
}

export function toNormalizedAssistantPreferencesDraft(
  preferences: AssistantPreferences,
  reasoningControl: AssistantReasoningControl,
): AssistantPreferencesDraft {
  return normalizeAssistantPreferencesDraft(toAssistantPreferencesDraft(preferences), reasoningControl);
}

export function buildAssistantPreferencesPayload(
  draft: AssistantPreferencesDraft,
  reasoningControl: AssistantReasoningControl,
) {
  const normalizedDraft = normalizeAssistantPreferencesDraft(draft, reasoningControl);
  const reasoningPayload = buildAssistantReasoningPayload(
    {
      reasoningEffort: normalizedDraft.defaultReasoningEffort,
      thinkingBudget: normalizedDraft.defaultThinkingBudget,
      thinkingLevel: normalizedDraft.defaultThinkingLevel,
    },
    reasoningControl,
    { preserveInvalidShape: true },
  );
  return {
    default_model_name: normalizeDraftValue(normalizedDraft.defaultModelName),
    default_max_output_tokens: normalizeTokenDraftValue(normalizedDraft.defaultMaxOutputTokens),
    default_provider: normalizeDraftValue(normalizedDraft.defaultProvider),
    default_reasoning_effort: reasoningPayload.reasoning_effort ?? null,
    default_thinking_level: reasoningPayload.thinking_level ?? null,
    default_thinking_budget: reasoningPayload.thinking_budget ?? null,
  };
}

export function isAssistantPreferencesDirty(
  draft: AssistantPreferencesDraft,
  preferences: AssistantPreferences,
  reasoningControl: AssistantReasoningControl,
): boolean {
  const currentPayload = buildAssistantPreferencesPayload(draft, reasoningControl);
  const savedPayload = buildAssistantPreferencesPayload(
    toNormalizedAssistantPreferencesDraft(preferences, reasoningControl),
    reasoningControl,
  );
  return (
    currentPayload.default_provider !== savedPayload.default_provider
    || currentPayload.default_model_name !== savedPayload.default_model_name
    || currentPayload.default_max_output_tokens !== savedPayload.default_max_output_tokens
    || currentPayload.default_reasoning_effort !== savedPayload.default_reasoning_effort
    || currentPayload.default_thinking_level !== savedPayload.default_thinking_level
    || currentPayload.default_thinking_budget !== savedPayload.default_thinking_budget
  );
}

export function buildAssistantProviderOptions(
  credentials: CredentialView[] | undefined,
  scope: AssistantPreferencesScope = "user",
): AssistantProviderOption[] {
  const optionByProvider = new Map<string, AssistantProviderOption>();

  for (const credential of credentials ?? []) {
    if (!credential.is_active) {
      continue;
    }
    const provider = credential.provider.trim();
    if (!provider || optionByProvider.has(provider)) {
      continue;
    }
    optionByProvider.set(provider, {
      apiDialect: credential.api_dialect,
      ...(credential.default_model?.trim()
        ? { defaultModel: credential.default_model.trim() }
        : {}),
      description: buildProviderDescription(credential, scope),
      label: credential.display_name.trim() || provider,
      value: provider,
    });
  }

  return [
    scope === "project" ? FOLLOW_USER_PROVIDER_OPTION : FOLLOW_SYSTEM_PROVIDER_OPTION,
    ...Array.from(optionByProvider.values()).sort((left, right) =>
      left.label.localeCompare(right.label, "zh-CN"),
    ),
  ];
}

export function buildAssistantPreferencesFormKey(preferences: AssistantPreferences | undefined) {
  if (!preferences) {
    return "assistant-preferences:empty";
  }
  return [
    preferences.default_provider ?? "none",
    preferences.default_model_name ?? "none",
    preferences.default_max_output_tokens ?? "none",
    preferences.default_reasoning_effort ?? "none",
    preferences.default_thinking_level ?? "none",
    preferences.default_thinking_budget ?? "none",
  ].join(":");
}

function normalizeDraftValue(value: string) {
  const normalized = value.trim();
  return normalized ? normalized : null;
}

export function normalizeAssistantMaxOutputTokenDraft(value: string) {
  return sanitizeAssistantOutputTokenInput(value);
}

function normalizeTokenDraftValue(value: string) {
  const normalized = sanitizeAssistantOutputTokenInput(value);
  if (!normalized) {
    return null;
  }
  const parsed = Number.parseInt(normalized, 10);
  if (!Number.isFinite(parsed)) {
    return null;
  }
  return parsed;
}

function toAssistantPreferencesTokenDraft(value: number | null) {
  if (value === null) {
    return "";
  }
  return String(value);
}

export function toAssistantPreferencesThinkingBudgetDraft(value: number | null) {
  if (value === null) {
    return "";
  }
  return String(value);
}

export function normalizeAssistantThinkingBudgetDraft(value: string) {
  return parseAssistantThinkingBudgetDraft(value);
}

function buildProviderDescription(
  credential: Pick<CredentialView, "default_model" | "owner_type" | "provider">,
  scope: AssistantPreferencesScope,
) {
  const provider = credential.provider.trim();
  const normalizedModel = credential.default_model?.trim() ?? "";
  const sourceLabel = resolveProviderSourceLabel(credential.owner_type, scope);
  if (!normalizedModel) {
    return `${sourceLabel} · ${provider}`;
  }
  return `${sourceLabel} · ${provider} · 默认模型：${normalizedModel}`;
}

function resolveProviderSourceLabel(
  ownerType: CredentialView["owner_type"],
  scope: AssistantPreferencesScope,
) {
  if (scope !== "project") {
    return "已启用连接";
  }
  if (ownerType === "project") {
    return "项目连接";
  }
  if (ownerType === "user") {
    return "个人连接";
  }
  return "已启用连接";
}
