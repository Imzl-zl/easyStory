import { formatObservabilityDateTime } from "@/features/observability/components/observability-datetime-support";
import type { CredentialApiDialect, CredentialView } from "@/lib/api/types";

export type CredentialCenterMode = "list" | "audit";

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
};

export function createInitialCredentialForm(): CredentialFormState {
  return {
    provider: "",
    apiDialect: "openai_chat_completions",
    displayName: "",
    apiKey: "",
    baseUrl: DEFAULT_BASE_URLS.openai_chat_completions,
    defaultModel: "",
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

export function formatAuditTime(value: string) {
  return formatObservabilityDateTime(value);
}
