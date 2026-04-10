import type {
  AssistantPreferences,
  CredentialVerifyProbeKind,
  CredentialView,
} from "@/lib/api/types";
import {
  normalizeAssistantReasoningDraft,
  resolveAssistantReasoningControl,
} from "@/features/shared/assistant/assistant-reasoning-support";

export type CredentialToolTransportMode = "stream" | "buffered";

type AssistantCredentialSettings = {
  maxOutputTokens: string;
  modelName: string;
  provider: string;
  reasoningEffort: string;
  streamOutput: boolean;
  thinkingBudget: string;
  thinkingLevel: string;
};

export type IncubatorCredentialOption = {
  apiDialect: string;
  baseUrl: string | null;
  bufferedToolVerifiedProbeKind: CredentialVerifyProbeKind | null;
  defaultModel: string;
  defaultMaxOutputTokens: number | null;
  displayLabel: string;
  provider: string;
  streamToolVerifiedProbeKind: CredentialVerifyProbeKind | null;
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
      bufferedToolVerifiedProbeKind: credential.buffered_tool_verified_probe_kind ?? null,
      defaultModel: credential.default_model?.trim() ?? "",
      defaultMaxOutputTokens: credential.default_max_output_tokens,
      displayLabel: buildCredentialDisplayLabel(
        credential.display_name,
        credential.default_model,
      ),
      provider: credential.provider,
      streamToolVerifiedProbeKind: credential.stream_tool_verified_probe_kind ?? null,
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
  if (currentOption) {
    return currentOption;
  }
  if (options.preferredProvider.trim()) {
    const preferredOption = pickIncubatorCredentialOption(options.options, options.preferredProvider);
    if (preferredOption && (options.hasUserMessage || !isInsecurePublicHttpCredentialOption(preferredOption))) {
      return preferredOption;
    }
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
  current: AssistantCredentialSettings,
  selectedCredential: IncubatorCredentialOption | null,
  preferences?: AssistantPreferences,
): AssistantCredentialSettings | null {
  if (!selectedCredential) {
    return null;
  }

  const currentProvider = current.provider.trim();
  const currentModelName = current.modelName.trim();
  const currentMaxOutputTokens = current.maxOutputTokens.trim();
  const preferredProvider = preferences?.default_provider?.trim() ?? "";
  const preferredModelName = preferences?.default_model_name?.trim() ?? "";
  const nextProvider = selectedCredential.provider;
  const appliesPreferredDefaults = preferredProvider
    ? preferredProvider === nextProvider
    : supportsProviderAgnosticPreferredModel({
      apiDialect: selectedCredential.apiDialect,
      preferredModelName,
    });
  const fallbackModelName = appliesPreferredDefaults
    ? preferredModelName || selectedCredential.defaultModel
    : selectedCredential.defaultModel;
  const nextModelName = currentProvider === nextProvider
    ? currentModelName || fallbackModelName
    : fallbackModelName;
  const nextStreamOutput = currentProvider === nextProvider
    ? current.streamOutput
    : !prefersBufferedOutput(selectedCredential);
  const nextReasoningDraft = normalizeAssistantReasoningDraft(
    currentProvider === nextProvider
      ? {
        reasoningEffort: current.reasoningEffort,
        thinkingBudget: current.thinkingBudget,
        thinkingLevel: current.thinkingLevel,
      }
      : {
        reasoningEffort: appliesPreferredDefaults
          ? preferences?.default_reasoning_effort ?? ""
          : "",
        thinkingBudget: appliesPreferredDefaults && preferences?.default_thinking_budget != null
          ? String(preferences?.default_thinking_budget ?? "")
          : "",
        thinkingLevel: appliesPreferredDefaults
          ? preferences?.default_thinking_level ?? ""
          : "",
      },
    resolveAssistantReasoningControl({
      apiDialect: selectedCredential.apiDialect,
      modelName: nextModelName,
    }),
  );

  if (
    nextProvider === currentProvider
    && nextModelName === currentModelName
    && nextStreamOutput === current.streamOutput
    && nextReasoningDraft.reasoningEffort === current.reasoningEffort
    && nextReasoningDraft.thinkingLevel === current.thinkingLevel
    && nextReasoningDraft.thinkingBudget === current.thinkingBudget
  ) {
    return null;
  }

  return {
    maxOutputTokens: currentMaxOutputTokens,
    modelName: nextModelName,
    provider: nextProvider,
    reasoningEffort: nextReasoningDraft.reasoningEffort,
    streamOutput: nextStreamOutput,
    thinkingBudget: nextReasoningDraft.thinkingBudget,
    thinkingLevel: nextReasoningDraft.thinkingLevel,
  };
}

export function prefersBufferedOutput(_option: IncubatorCredentialOption | null) {
  return false;
}

function supportsProviderAgnosticPreferredModel(options: {
  apiDialect: string;
  preferredModelName: string;
}) {
  const preferredModelName = options.preferredModelName.trim().toLowerCase();
  if (!preferredModelName) {
    return true;
  }
  if (options.apiDialect === "openai_chat_completions" || options.apiDialect === "openai_responses") {
    return !preferredModelName.startsWith("claude-") && !preferredModelName.startsWith("gemini-");
  }
  if (options.apiDialect === "anthropic_messages") {
    return preferredModelName.startsWith("claude-");
  }
  if (options.apiDialect === "gemini_generate_content") {
    return preferredModelName.startsWith("gemini-");
  }
  return false;
}

export function resolveCredentialToolTransportMode(
  streamOutput: boolean,
): CredentialToolTransportMode {
  return streamOutput ? "stream" : "buffered";
}

export function supportsCredentialToolTransportMode(
  credential: Pick<IncubatorCredentialOption, "bufferedToolVerifiedProbeKind" | "streamToolVerifiedProbeKind"> | null,
  transportMode: CredentialToolTransportMode,
) {
  return resolveConformanceProbeRank(
    resolveCredentialToolVerifiedProbeKind(credential, transportMode),
  ) >= resolveConformanceProbeRank("tool_continuation_probe");
}

export function buildCredentialToolCapabilityNotice(options: {
  credential: Pick<IncubatorCredentialOption, "bufferedToolVerifiedProbeKind" | "displayLabel" | "streamToolVerifiedProbeKind"> | null;
  streamOutput: boolean;
}) {
  if (!options.credential) {
    return null;
  }
  const transportMode = resolveCredentialToolTransportMode(options.streamOutput);
  if (supportsCredentialToolTransportMode(options.credential, transportMode)) {
    return null;
  }
  const modeLabel = transportMode === "stream" ? "边写边显示" : "生成后整体显示";
  const verifyLabel = transportMode === "stream" ? "验证流式工具" : "验证非流工具";
  return `当前连接“${options.credential.displayLabel}”尚未通过“${verifyLabel}”，不能在“${modeLabel}”模式下启用项目工具。`;
}

function resolveCredentialToolVerifiedProbeKind(
  credential: Pick<IncubatorCredentialOption, "bufferedToolVerifiedProbeKind" | "streamToolVerifiedProbeKind"> | null,
  transportMode: CredentialToolTransportMode,
) {
  if (!credential) {
    return null;
  }
  if (transportMode === "buffered") {
    return credential.bufferedToolVerifiedProbeKind;
  }
  return credential.streamToolVerifiedProbeKind;
}

function resolveConformanceProbeRank(
  probeKind: CredentialVerifyProbeKind | null | undefined,
) {
  if (probeKind === "tool_continuation_probe") {
    return 3;
  }
  if (probeKind === "tool_call_probe") {
    return 2;
  }
  if (probeKind === "tool_definition_probe") {
    return 1;
  }
  if (probeKind === "text_probe") {
    return 0;
  }
  return -1;
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
