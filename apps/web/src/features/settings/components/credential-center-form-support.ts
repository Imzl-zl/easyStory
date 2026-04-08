import {
  areHeaderMapsEqual,
  formatExtraHeaders,
  getDefaultAuthStrategy,
  normalizeApiKeyHeaderName,
  normalizeCredentialAuthStrategy,
  normalizeCredentialInteropProfile,
  parseExtraHeadersText,
  type CredentialAuthStrategyValue,
  type CredentialInteropProfileValue,
} from "@/features/settings/components/credential-center-compatibility-support";
import { normalizeCredentialClientIdentity, type CredentialRuntimeKindValue } from "@/features/settings/components/credential-center-client-identity-support";
import { normalizeCredentialUserAgentOverride } from "@/features/settings/components/credential-center-user-agent-support";
import { parseContextWindowTokensDraft, parseDefaultMaxOutputTokensDraft, toCredentialTokenDraft } from "@/features/settings/components/credential-center-token-support";
import type { CredentialApiDialect, CredentialCreatePayload, CredentialUpdatePayload, CredentialView } from "@/lib/api/types";

export type CredentialCenterScope = "user" | "project";
export const API_DIALECT_OPTIONS: Array<{
  value: CredentialApiDialect;
  label: string;
  description: string;
}> = [
  {
    value: "openai_chat_completions",
    label: "OpenAI 兼容服务",
    description: "适合大多数兼容 OpenAI 接口的模型服务",
  },
  {
    value: "openai_responses",
    label: "OpenAI Responses 服务",
    description: "适合明确要求 Responses 接口的服务",
  },
  {
    value: "anthropic_messages",
    label: "Claude / Anthropic 服务",
    description: "适合 Claude 或兼容 Anthropic 接口的服务",
  },
  {
    value: "gemini_generate_content",
    label: "Gemini / Google 服务",
    description: "适合 Gemini 或兼容 Google AI 接口的服务",
  },
] as const;

const DEFAULT_BASE_URLS: Record<CredentialApiDialect, string> = {
  openai_chat_completions: "https://api.openai.com",
  openai_responses: "https://api.openai.com",
  anthropic_messages: "https://api.anthropic.com",
  gemini_generate_content: "https://generativelanguage.googleapis.com",
};
export type CredentialFormState = {
  provider: string;
  apiDialect: CredentialApiDialect;
  displayName: string;
  apiKey: string;
  baseUrl: string;
  defaultModel: string;
  interopProfile: CredentialInteropProfileValue;
  contextWindowTokens: string;
  defaultMaxOutputTokens: string;
  authStrategy: CredentialAuthStrategyValue;
  apiKeyHeaderName: string;
  extraHeadersText: string;
  userAgentOverride: string;
  clientName: string;
  clientVersion: string;
  runtimeKind: CredentialRuntimeKindValue;
};
export function createInitialCredentialForm(): CredentialFormState {
  return {
    provider: "",
    apiDialect: "openai_chat_completions",
    displayName: "",
    apiKey: "",
    baseUrl: DEFAULT_BASE_URLS.openai_chat_completions,
    defaultModel: "",
    interopProfile: "",
    contextWindowTokens: "",
    defaultMaxOutputTokens: "",
    authStrategy: "",
    apiKeyHeaderName: "",
    extraHeadersText: "",
    userAgentOverride: "",
    clientName: "",
    clientVersion: "",
    runtimeKind: "",
  };
}
export function createCredentialFormFromView(credential: CredentialView): CredentialFormState {
  return {
    provider: credential.provider,
    apiDialect: credential.api_dialect,
    displayName: credential.display_name,
    apiKey: "",
    baseUrl: credential.base_url ?? getDefaultBaseUrl(credential.api_dialect),
    defaultModel: credential.default_model ?? "",
    interopProfile: credential.interop_profile ?? "",
    contextWindowTokens: toCredentialTokenDraft(credential.context_window_tokens),
    defaultMaxOutputTokens: toCredentialTokenDraft(credential.default_max_output_tokens),
    authStrategy: credential.auth_strategy ?? "",
    apiKeyHeaderName: credential.api_key_header_name ?? "",
    extraHeadersText: formatExtraHeaders(credential.extra_headers),
    userAgentOverride: credential.user_agent_override ?? "",
    clientName: credential.client_name ?? "",
    clientVersion: credential.client_version ?? "",
    runtimeKind: credential.runtime_kind ?? "",
  };
}

export function isCredentialFormDirty(
  formState: CredentialFormState,
  initialState: CredentialFormState,
  credential?: CredentialView | null,
): boolean {
  const hasRawChanges = (
    formState.provider !== initialState.provider
    || formState.apiDialect !== initialState.apiDialect
    || formState.displayName !== initialState.displayName
    || formState.apiKey !== initialState.apiKey
    || formState.baseUrl !== initialState.baseUrl
    || formState.defaultModel !== initialState.defaultModel
    || formState.interopProfile !== initialState.interopProfile
    || formState.contextWindowTokens !== initialState.contextWindowTokens
    || formState.defaultMaxOutputTokens !== initialState.defaultMaxOutputTokens
    || formState.authStrategy !== initialState.authStrategy
    || formState.apiKeyHeaderName !== initialState.apiKeyHeaderName
    || formState.extraHeadersText !== initialState.extraHeadersText
    || formState.userAgentOverride !== initialState.userAgentOverride
    || formState.clientName !== initialState.clientName
    || formState.clientVersion !== initialState.clientVersion
    || formState.runtimeKind !== initialState.runtimeKind
  );
  if (!hasRawChanges || !credential) {
    return hasRawChanges;
  }
  try {
    return getCredentialUpdatePayloadSize(buildCredentialUpdatePayload(credential, formState)) > 0;
  } catch {
    return true;
  }
}
export function getApiDialectLabel(value: CredentialApiDialect) {
  return API_DIALECT_OPTIONS.find((option) => option.value === value)?.label ?? value;
}
export function getDefaultBaseUrl(apiDialect: CredentialApiDialect) {
  return DEFAULT_BASE_URLS[apiDialect];
}
export function normalizeCredentialBaseUrl(
  apiDialect: CredentialApiDialect,
  baseUrl: string,
): string | null {
  const normalized = baseUrl.trim();
  if (!normalized || normalized === getDefaultBaseUrl(apiDialect)) {
    return null;
  }
  return normalized;
}
export function formatCredentialBaseUrl(
  apiDialect: CredentialApiDialect,
  baseUrl: string | null,
): string {
  if (baseUrl === null || baseUrl === getDefaultBaseUrl(apiDialect)) {
    return "官方默认";
  }
  return baseUrl;
}
export function buildCredentialCreatePayload(options: {
  formState: CredentialFormState;
  projectId: string | null;
  scope: CredentialCenterScope;
}): CredentialCreatePayload {
  const { formState, projectId, scope } = options;
  const authStrategy = normalizeCredentialAuthStrategy(formState.apiDialect, formState.authStrategy);
  const apiKeyHeaderName = normalizeApiKeyHeaderName(
    formState.apiDialect,
    authStrategy,
    formState.apiKeyHeaderName,
  );
  const clientIdentity = normalizeCredentialClientIdentity({
    clientName: formState.clientName,
    clientVersion: formState.clientVersion,
    runtimeKind: formState.runtimeKind,
  });
  const payload: CredentialCreatePayload = {
    owner_type: scope,
    project_id: scope === "project" ? projectId : null,
    provider: formState.provider.trim(),
    api_dialect: formState.apiDialect,
    display_name: formState.displayName.trim(),
    api_key: formState.apiKey,
    base_url: normalizeCredentialBaseUrl(formState.apiDialect, formState.baseUrl),
    default_model: formState.defaultModel.trim(),
    context_window_tokens: parseContextWindowTokensDraft(formState.contextWindowTokens),
    default_max_output_tokens: parseDefaultMaxOutputTokensDraft(formState.defaultMaxOutputTokens),
    auth_strategy: authStrategy,
    api_key_header_name: apiKeyHeaderName,
    extra_headers: parseExtraHeadersText(formState.extraHeadersText, {
      apiDialect: formState.apiDialect,
      authStrategy,
      apiKeyHeaderName,
    }),
    user_agent_override: normalizeCredentialUserAgentOverride(formState.userAgentOverride),
    client_name: clientIdentity.clientName,
    client_version: clientIdentity.clientVersion,
    runtime_kind: clientIdentity.runtimeKind,
  };
  const interopProfile = normalizeCredentialInteropProfile(
    formState.apiDialect,
    formState.interopProfile,
  );
  if (interopProfile !== null) {
    payload.interop_profile = interopProfile;
  }
  return payload;
}

export function buildCredentialUpdatePayload(
  credential: CredentialView,
  formState: CredentialFormState,
): CredentialUpdatePayload {
  const payload: CredentialUpdatePayload = {};
  const displayName = formState.displayName.trim();
  const nextBaseUrl = normalizeCredentialBaseUrl(formState.apiDialect, formState.baseUrl);
  const nextDefaultModel = formState.defaultModel.trim();
  const nextInteropProfile = normalizeCredentialInteropProfile(
    formState.apiDialect,
    formState.interopProfile,
  );
  const nextContextWindowTokens = parseContextWindowTokensDraft(formState.contextWindowTokens);
  const nextDefaultMaxOutputTokens = parseDefaultMaxOutputTokensDraft(formState.defaultMaxOutputTokens);
  const nextAuthStrategy = normalizeCredentialAuthStrategy(formState.apiDialect, formState.authStrategy);
  const nextApiKeyHeaderName = normalizeApiKeyHeaderName(
    formState.apiDialect,
    nextAuthStrategy,
    formState.apiKeyHeaderName,
  );
  const nextUserAgentOverride = normalizeCredentialUserAgentOverride(formState.userAgentOverride);
  const nextClientIdentity = normalizeCredentialClientIdentity({
    clientName: formState.clientName,
    clientVersion: formState.clientVersion,
    runtimeKind: formState.runtimeKind,
  });
  const nextExtraHeaders = parseExtraHeadersText(formState.extraHeadersText, {
    apiDialect: formState.apiDialect,
    authStrategy: nextAuthStrategy,
    apiKeyHeaderName: nextApiKeyHeaderName,
  });
  if (formState.apiDialect !== credential.api_dialect) {
    payload.api_dialect = formState.apiDialect;
  }
  if (displayName !== credential.display_name) {
    payload.display_name = displayName;
  }
  if (nextBaseUrl !== credential.base_url) {
    payload.base_url = nextBaseUrl;
  }
  appendDefaultModelUpdate(payload, credential.default_model, nextDefaultModel);
  if (nextInteropProfile !== (credential.interop_profile ?? null)) {
    payload.interop_profile = nextInteropProfile;
  }
  if (nextContextWindowTokens !== credential.context_window_tokens) {
    payload.context_window_tokens = nextContextWindowTokens;
  }
  if (nextDefaultMaxOutputTokens !== credential.default_max_output_tokens) {
    payload.default_max_output_tokens = nextDefaultMaxOutputTokens;
  }
  if (nextAuthStrategy !== credential.auth_strategy) {
    payload.auth_strategy = nextAuthStrategy;
  }
  if (nextApiKeyHeaderName !== credential.api_key_header_name) {
    payload.api_key_header_name = nextApiKeyHeaderName;
  }
  if (!areHeaderMapsEqual(nextExtraHeaders, credential.extra_headers)) {
    payload.extra_headers = nextExtraHeaders;
  }
  if (nextUserAgentOverride !== credential.user_agent_override) {
    payload.user_agent_override = nextUserAgentOverride;
  }
  if (nextClientIdentity.clientName !== credential.client_name) {
    payload.client_name = nextClientIdentity.clientName;
  }
  if (nextClientIdentity.clientVersion !== credential.client_version) {
    payload.client_version = nextClientIdentity.clientVersion;
  }
  if (nextClientIdentity.runtimeKind !== credential.runtime_kind) {
    payload.runtime_kind = nextClientIdentity.runtimeKind;
  }
  if (formState.apiKey.trim()) {
    payload.api_key = formState.apiKey;
  }
  return payload;
}
export function getCredentialUpdatePayloadSize(payload: CredentialUpdatePayload): number {
  return Object.keys(payload).length;
}

export function normalizeOptionalQueryValue(value: string | null): string | null {
  const normalized = value?.trim() ?? "";
  return normalized ? normalized : null;
}
function appendDefaultModelUpdate(
  payload: CredentialUpdatePayload,
  currentValue: string | null,
  nextValue: string,
) {
  if (!nextValue) {
    if (currentValue !== null) {
      throw new Error("当前更新接口不支持清空默认模型；请保留原值或填写新的默认模型。");
    }
    return;
  }
  if (nextValue !== currentValue) {
    payload.default_model = nextValue;
  }
}
