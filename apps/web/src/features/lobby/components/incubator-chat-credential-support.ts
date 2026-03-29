import type { AssistantPreferences, CredentialView } from "@/lib/api/types";
import { DEFAULT_ASSISTANT_MAX_OUTPUT_TOKENS } from "@/features/shared/assistant/assistant-output-token-support";

import type { IncubatorChatSettings } from "./incubator-chat-support";

export type IncubatorCredentialOption = {
  apiDialect: string;
  baseUrl: string | null;
  defaultModel: string;
  defaultMaxOutputTokens: number | null;
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
      apiDialect: credential.api_dialect,
      baseUrl: credential.base_url,
      defaultModel: credential.default_model?.trim() ?? "",
      defaultMaxOutputTokens: credential.default_max_output_tokens,
      displayLabel: buildCredentialDisplayLabel(
        credential.display_name,
        credential.default_model,
      ),
      provider: credential.provider,
    });
  }

  return Array.from(optionByProvider.values()).sort(compareIncubatorCredentialOptions);
}

export function pickIncubatorCredentialOption(
  options: IncubatorCredentialOption[],
  provider: string,
): IncubatorCredentialOption | null {
  const normalizedProvider = provider.trim();
  const fallbackOption = [...options].sort(compareIncubatorCredentialOptions)[0] ?? null;
  if (!options.length) {
    return null;
  }
  if (!normalizedProvider) {
    return fallbackOption;
  }
  return options.find((option) => option.provider === normalizedProvider) ?? fallbackOption;
}

export function resolveSelectedIncubatorCredentialOption(options: {
  currentProvider: string;
  hasUserMessage: boolean;
  options: IncubatorCredentialOption[];
  preferredProvider: string;
}) {
  const currentOption = options.options.find((option) => option.provider === options.currentProvider.trim()) ?? null;
  if (options.preferredProvider.trim()) {
    return pickIncubatorCredentialOption(options.options, options.preferredProvider);
  }
  if (currentOption && (options.hasUserMessage || !isInsecurePublicHttpCredentialOption(currentOption))) {
    return currentOption;
  }
  return pickIncubatorCredentialOption(options.options, "");
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
  current: Pick<IncubatorChatSettings, "maxOutputTokens" | "modelName" | "provider" | "streamOutput">,
  selectedCredential: IncubatorCredentialOption | null,
  preferences?: AssistantPreferences,
): Pick<IncubatorChatSettings, "maxOutputTokens" | "modelName" | "provider" | "streamOutput"> | null {
  if (!selectedCredential) {
    return null;
  }

  const currentProvider = current.provider.trim();
  const currentModelName = current.modelName.trim();
  const currentMaxOutputTokens = current.maxOutputTokens.trim();
  const preferredProvider = preferences?.default_provider?.trim() ?? "";
  const preferredModelName = preferences?.default_model_name?.trim() ?? "";
  const preferredMaxOutputTokens = String(
    preferences?.default_max_output_tokens
      ?? selectedCredential.defaultMaxOutputTokens
      ?? DEFAULT_ASSISTANT_MAX_OUTPUT_TOKENS,
  );
  const nextProvider = selectedCredential.provider;
  const fallbackModelName = preferredProvider === nextProvider
    ? preferredModelName || selectedCredential.defaultModel
    : selectedCredential.defaultModel;
  const nextModelName = currentProvider === nextProvider
    ? currentModelName || fallbackModelName
    : fallbackModelName;
  const nextMaxOutputTokens = currentMaxOutputTokens || preferredMaxOutputTokens;
  const nextStreamOutput = currentProvider === nextProvider
    ? current.streamOutput
    : !prefersBufferedOutput(selectedCredential);

  if (
    nextProvider === currentProvider
    && nextModelName === currentModelName
    && nextMaxOutputTokens === currentMaxOutputTokens
    && nextStreamOutput === current.streamOutput
  ) {
    return null;
  }

  return {
    maxOutputTokens: nextMaxOutputTokens,
    modelName: nextModelName,
    provider: nextProvider,
    streamOutput: nextStreamOutput,
  };
}

export function prefersBufferedOutput(option: IncubatorCredentialOption | null) {
  return option?.apiDialect === "gemini_generate_content";
}

function compareIncubatorCredentialOptions(
  left: IncubatorCredentialOption,
  right: IncubatorCredentialOption,
) {
  const endpointPriorityDiff = resolveCredentialEndpointPriority(left) - resolveCredentialEndpointPriority(right);
  if (endpointPriorityDiff !== 0) {
    return endpointPriorityDiff;
  }
  const outputPriorityDiff = Number(prefersBufferedOutput(left)) - Number(prefersBufferedOutput(right));
  if (outputPriorityDiff !== 0) {
    return outputPriorityDiff;
  }
  return left.displayLabel.localeCompare(right.displayLabel, "zh-CN");
}

function resolveCredentialEndpointPriority(option: IncubatorCredentialOption) {
  const normalizedBaseUrl = option.baseUrl?.trim() ?? "";
  if (!normalizedBaseUrl) {
    return 0;
  }
  try {
    const parsedUrl = new URL(normalizedBaseUrl);
    if (parsedUrl.protocol === "https:") {
      return 0;
    }
    if (parsedUrl.protocol !== "http:") {
      return 2;
    }
    return isPrivateHostname(parsedUrl.hostname) ? 1 : 2;
  } catch {
    return 2;
  }
}

function isInsecurePublicHttpCredentialOption(option: IncubatorCredentialOption) {
  return resolveCredentialEndpointPriority(option) === 2;
}

function isPrivateHostname(hostname: string) {
  const normalizedHost = hostname.trim().toLowerCase();
  if (!normalizedHost) {
    return false;
  }
  if (
    normalizedHost === "localhost"
    || normalizedHost === "host.docker.internal"
    || normalizedHost === "::1"
    || normalizedHost === "127.0.0.1"
  ) {
    return true;
  }
  if (normalizedHost.endsWith(".localhost") || normalizedHost.endsWith(".local")) {
    return true;
  }
  if (normalizedHost.startsWith("10.") || normalizedHost.startsWith("192.168.")) {
    return true;
  }
  if (normalizedHost.startsWith("172.")) {
    const secondOctet = Number.parseInt(normalizedHost.split(".")[1] ?? "", 10);
    return Number.isInteger(secondOctet) && secondOctet >= 16 && secondOctet <= 31;
  }
  return false;
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
