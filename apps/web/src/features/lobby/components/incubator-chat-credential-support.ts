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
      displayLabel: `${credential.display_name} · ${credential.provider}`,
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
  return "当前账号还没有启用任何模型凭证。先去凭证中心启用一个 provider，再回来和 AI 聊故事。";
}
