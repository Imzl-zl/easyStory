import type { CredentialView } from "@/lib/api/types";

export type IncubatorCredentialOption = {
  defaultModel: string;
  displayLabel: string;
  provider: string;
};

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
  isLoading: boolean,
  options: IncubatorCredentialOption[],
): string | null {
  if (isLoading || options.length > 0) {
    return null;
  }
  return "当前账号还没有启用任何模型连接。先去模型连接里启用一条，再回来继续聊天。";
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
