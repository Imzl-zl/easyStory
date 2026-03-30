import type {
  AssistantPreferences,
  AssistantPreferencesUpdatePayload,
  CredentialView,
} from "@/lib/api/types";
import {
  sanitizeAssistantOutputTokenInput,
} from "@/features/shared/assistant/assistant-output-token-support";

export type AssistantPreferencesScope = "user" | "project";

export type AssistantPreferencesDraft = {
  defaultModelName: string;
  defaultMaxOutputTokens: string;
  defaultProvider: string;
};

export type AssistantProviderOption = {
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
  };
}

export function buildAssistantPreferencesPayload(
  draft: AssistantPreferencesDraft,
): AssistantPreferencesUpdatePayload {
  return {
    default_model_name: normalizeDraftValue(draft.defaultModelName),
    default_max_output_tokens: normalizeTokenDraftValue(draft.defaultMaxOutputTokens),
    default_provider: normalizeDraftValue(draft.defaultProvider),
  };
}

export function isAssistantPreferencesDirty(
  draft: AssistantPreferencesDraft,
  preferences: AssistantPreferences,
): boolean {
  return (
    normalizeDraftValue(draft.defaultProvider) !== preferences.default_provider
    || normalizeDraftValue(draft.defaultModelName) !== preferences.default_model_name
    || normalizeTokenDraftValue(draft.defaultMaxOutputTokens) !== preferences.default_max_output_tokens
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
