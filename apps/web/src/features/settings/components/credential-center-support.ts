import { formatObservabilityDateTime } from "@/features/observability/components/observability-datetime-support";
import {
  areHeaderMapsEqual,
  AUTH_STRATEGY_OPTIONS,
  formatExtraHeaders,
  getDefaultAuthStrategy,
  normalizeApiKeyHeaderName,
  normalizeCredentialAuthStrategy,
  parseExtraHeadersText,
  type CredentialAuthStrategyValue,
} from "@/features/settings/components/credential-center-compatibility-support";
import type {
  CredentialApiDialect,
  CredentialCreatePayload,
  CredentialUpdatePayload,
  CredentialView,
} from "@/lib/api/types";

export {
  AUTH_STRATEGY_OPTIONS,
  getDefaultAuthStrategy,
  type CredentialAuthStrategyValue,
} from "@/features/settings/components/credential-center-compatibility-support";

export type CredentialCenterMode = "list" | "audit";
export type CredentialCenterScope = "user" | "project";

export const API_DIALECT_OPTIONS: Array<{
  value: CredentialApiDialect;
  label: string;
  description: string;
}> = [
  {
    value: "openai_chat_completions",
    label: "OpenAI Chat Completions",
    description: "POST /v1/chat/completions",
  },
  {
    value: "openai_responses",
    label: "OpenAI Responses",
    description: "POST /v1/responses",
  },
  {
    value: "anthropic_messages",
    label: "Anthropic Messages",
    description: "POST /v1/messages",
  },
  {
    value: "gemini_generate_content",
    label: "Gemini Generate Content",
    description: "POST /v1beta/models/{model}:generateContent",
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
  authStrategy: CredentialAuthStrategyValue;
  apiKeyHeaderName: string;
  extraHeadersText: string;
};

export function createInitialCredentialForm(): CredentialFormState {
  return {
    provider: "",
    apiDialect: "openai_chat_completions",
    displayName: "",
    apiKey: "",
    baseUrl: DEFAULT_BASE_URLS.openai_chat_completions,
    defaultModel: "",
    authStrategy: "",
    apiKeyHeaderName: "",
    extraHeadersText: "",
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
    authStrategy: credential.auth_strategy ?? "",
    apiKeyHeaderName: credential.api_key_header_name ?? "",
    extraHeadersText: formatExtraHeaders(credential.extra_headers),
  };
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
  return {
    owner_type: scope,
    project_id: scope === "project" ? projectId : null,
    provider: formState.provider.trim(),
    api_dialect: formState.apiDialect,
    display_name: formState.displayName.trim(),
    api_key: formState.apiKey,
    base_url: normalizeCredentialBaseUrl(formState.apiDialect, formState.baseUrl),
    default_model: formState.defaultModel.trim(),
    auth_strategy: authStrategy,
    api_key_header_name: apiKeyHeaderName,
    extra_headers: parseExtraHeadersText(formState.extraHeadersText, {
      apiDialect: formState.apiDialect,
      authStrategy,
      apiKeyHeaderName,
    }),
  };
}

export function buildCredentialUpdatePayload(
  credential: CredentialView,
  formState: CredentialFormState,
): CredentialUpdatePayload {
  const payload: CredentialUpdatePayload = {};
  const displayName = formState.displayName.trim();
  const nextBaseUrl = normalizeCredentialBaseUrl(formState.apiDialect, formState.baseUrl);
  const nextDefaultModel = formState.defaultModel.trim();
  const nextAuthStrategy = normalizeCredentialAuthStrategy(formState.apiDialect, formState.authStrategy);
  const nextApiKeyHeaderName = normalizeApiKeyHeaderName(
    formState.apiDialect,
    nextAuthStrategy,
    formState.apiKeyHeaderName,
  );
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
  if (nextAuthStrategy !== credential.auth_strategy) {
    payload.auth_strategy = nextAuthStrategy;
  }
  if (nextApiKeyHeaderName !== credential.api_key_header_name) {
    payload.api_key_header_name = nextApiKeyHeaderName;
  }
  if (!areHeaderMapsEqual(nextExtraHeaders, credential.extra_headers)) {
    payload.extra_headers = nextExtraHeaders;
  }
  if (formState.apiKey.trim()) {
    payload.api_key = formState.apiKey;
  }
  return payload;
}

export function getCredentialUpdatePayloadSize(payload: CredentialUpdatePayload): number {
  return Object.keys(payload).length;
}

export function resolveActiveCredentialId(
  credentials: CredentialView[] | undefined,
  selectedCredentialId: string | null,
): string | null {
  if (!credentials || credentials.length === 0) {
    return null;
  }
  if (selectedCredentialId && credentials.some((credential) => credential.id === selectedCredentialId)) {
    return selectedCredentialId;
  }
  return credentials[0]?.id ?? null;
}

export function resolveEditableCredential(
  credentials: CredentialView[] | undefined,
  selectedCredentialId: string | null,
): CredentialView | null {
  if (!credentials || !selectedCredentialId) {
    return null;
  }
  return credentials.find((credential) => credential.id === selectedCredentialId) ?? null;
}

export function normalizeOptionalQueryValue(value: string | null): string | null {
  const normalized = value?.trim() ?? "";
  return normalized ? normalized : null;
}

export function formatAuditTime(value: string) {
  return formatObservabilityDateTime(value);
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
