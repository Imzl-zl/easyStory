import type {
  AssistantPreferences,
  AssistantPreferencesUpdatePayload,
  CredentialView,
} from "@/lib/api/types";

export type AssistantPreferencesDraft = {
  defaultModelName: string;
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

export function toAssistantPreferencesDraft(
  preferences: AssistantPreferences,
): AssistantPreferencesDraft {
  return {
    defaultModelName: preferences.default_model_name ?? "",
    defaultProvider: preferences.default_provider ?? "",
  };
}

export function buildAssistantPreferencesPayload(
  draft: AssistantPreferencesDraft,
): AssistantPreferencesUpdatePayload {
  return {
    default_model_name: normalizeDraftValue(draft.defaultModelName),
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
  );
}

export function buildAssistantProviderOptions(
  credentials: CredentialView[] | undefined,
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
      description: buildProviderDescription(provider, credential.default_model),
      label: credential.display_name.trim() || provider,
      value: provider,
    });
  }

  return [
    FOLLOW_SYSTEM_PROVIDER_OPTION,
    ...Array.from(optionByProvider.values()).sort((left, right) =>
      left.label.localeCompare(right.label, "zh-CN"),
    ),
  ];
}

function normalizeDraftValue(value: string) {
  const normalized = value.trim();
  return normalized ? normalized : null;
}

function buildProviderDescription(provider: string, defaultModel: string | null) {
  const normalizedModel = defaultModel?.trim() ?? "";
  if (!normalizedModel) {
    return `已启用连接 · ${provider}`;
  }
  return `已启用连接 · ${provider} · 默认模型：${normalizedModel}`;
}
