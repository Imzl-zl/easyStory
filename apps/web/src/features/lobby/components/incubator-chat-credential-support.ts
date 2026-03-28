import type { AssistantPreferences, CredentialView } from "@/lib/api/types";

import type { IncubatorChatSettings } from "./incubator-chat-support";

export type IncubatorCredentialOption = {
  defaultModel: string;
  displayLabel: string;
  provider: string;
};

export type IncubatorCredentialState = "empty" | "error" | "loading" | "ready";

export const INCUBATOR_CREDENTIAL_SETTINGS_HREF = "/workspace/lobby/settings?tab=credentials";

export function buildIncubatorCredentialOptions(
  credentials: CredentialView[] | undefined,
): IncubatorCredentialOption[] {
  const activeCredentials = (credentials ?? []).filter((credential) => credential.is_active);
  const optionByProvider = new Map<string, IncubatorCredentialOption>();

  for (const credential of activeCredentials) {
    if (optionByProvider.has(credential.provider)) {
      continue;
    }
    optionByProvider.set(credential.provider, {
      defaultModel: credential.default_model?.trim() ?? "",
      displayLabel: buildCredentialDisplayLabel(
        credential.display_name,
        credential.default_model,
      ),
      provider: credential.provider,
    });
  }

  return Array.from(optionByProvider.values());
}

export function pickIncubatorCredentialOption(
  options: IncubatorCredentialOption[],
  provider: string,
): IncubatorCredentialOption | null {
  const normalizedProvider = provider.trim();
  if (!options.length) {
    return null;
  }
  if (!normalizedProvider) {
    return options[0];
  }
  return options.find((option) => option.provider === normalizedProvider) ?? options[0];
}

export function buildIncubatorCredentialNotice(
  options: {
    errorMessage: string | null;
    isLoading: boolean;
    credentialOptions: IncubatorCredentialOption[];
  },
): string | null {
  const state = resolveIncubatorCredentialState(options);
  if (state === "loading" || state === "ready") {
    return null;
  }
  if (state === "error") {
    return `模型连接读取失败，请刷新后重试。错误信息：${options.errorMessage}`;
  }
  return "当前账号没有可用模型连接，请先启用。";
}

export function resolveIncubatorCredentialState(options: {
  errorMessage: string | null;
  isLoading: boolean;
  credentialOptions: IncubatorCredentialOption[];
}): IncubatorCredentialState {
  if (options.isLoading) {
    return "loading";
  }
  if (options.errorMessage) {
    return "error";
  }
  if (options.credentialOptions.length === 0) {
    return "empty";
  }
  return "ready";
}

export function resolveHydratedIncubatorChatSettings(
  current: Pick<IncubatorChatSettings, "modelName" | "provider">,
  selectedCredential: IncubatorCredentialOption | null,
  preferences?: AssistantPreferences,
): Pick<IncubatorChatSettings, "modelName" | "provider"> | null {
  if (!selectedCredential) {
    return null;
  }

  const currentProvider = current.provider.trim();
  const currentModelName = current.modelName.trim();
  const preferredProvider = preferences?.default_provider?.trim() ?? "";
  const preferredModelName = preferences?.default_model_name?.trim() ?? "";

  if (currentProvider === selectedCredential.provider) {
    return null;
  }

  const nextProvider = selectedCredential.provider;
  const nextModelName = preferredProvider === nextProvider
    ? preferredModelName || selectedCredential.defaultModel
    : selectedCredential.defaultModel;

  if (nextProvider === currentProvider && nextModelName === currentModelName) {
    return null;
  }

  return {
    modelName: nextModelName,
    provider: nextProvider,
  };
}

function buildCredentialDisplayLabel(
  displayName: string,
  defaultModel: string | null,
) {
  const normalizedDisplayName = displayName.trim();
  const normalizedModel = defaultModel?.trim() ?? "";
  if (!normalizedDisplayName && !normalizedModel) {
    return "未命名连接";
  }
  if (!normalizedDisplayName) {
    return normalizedModel;
  }
  if (!normalizedModel) {
    return normalizedDisplayName;
  }
  return `${normalizedDisplayName} · ${normalizedModel}`;
}
