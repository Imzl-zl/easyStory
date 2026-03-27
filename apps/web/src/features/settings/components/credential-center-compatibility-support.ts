import type { CredentialApiDialect, CredentialAuthStrategy } from "@/lib/api/types";

export type CredentialAuthStrategyValue = CredentialAuthStrategy | "";

const CONTENT_TYPE_HEADER_NAME = "content-type";
const ANTHROPIC_VERSION_HEADER_NAME = "anthropic-version";
const HTTP_HEADER_TOKEN_PATTERN = /^[!#$%&'*+.^_`|~0-9A-Za-z-]+$/;
const SENSITIVE_EXTRA_HEADER_NAMES = new Set([
  "authorization",
  "proxy-authorization",
  "cookie",
  "set-cookie",
  "x-api-key",
  "x-goog-api-key",
]);
const SENSITIVE_EXTRA_HEADER_FRAGMENTS = ["token", "secret", "api-key", "api_key"];

const DEFAULT_AUTH_STRATEGIES: Record<CredentialApiDialect, CredentialAuthStrategy> = {
  openai_chat_completions: "bearer",
  openai_responses: "bearer",
  anthropic_messages: "x_api_key",
  gemini_generate_content: "x_goog_api_key",
};

export const AUTH_STRATEGY_OPTIONS: Array<{
  value: CredentialAuthStrategyValue;
  label: string;
  description: string;
}> = [
  { value: "", label: "跟随默认设置", description: "按当前服务类型自动选择最常见的方式" },
  { value: "bearer", label: "放到 Authorization", description: "常见于 OpenAI 兼容服务" },
  { value: "x_api_key", label: "放到 x-api-key", description: "常见于 Anthropic 兼容服务" },
  { value: "x_goog_api_key", label: "放到 x-goog-api-key", description: "常见于 Gemini 兼容服务" },
  { value: "custom_header", label: "放到自定义请求头", description: "只有上游有特殊要求时再使用" },
] as const;

export function getDefaultAuthStrategy(apiDialect: CredentialApiDialect) {
  return DEFAULT_AUTH_STRATEGIES[apiDialect];
}

export function normalizeCredentialAuthStrategy(
  apiDialect: CredentialApiDialect,
  authStrategy: CredentialAuthStrategyValue,
): CredentialAuthStrategy | null {
  if (!authStrategy || authStrategy === getDefaultAuthStrategy(apiDialect)) {
    return null;
  }
  return authStrategy;
}

export function normalizeApiKeyHeaderName(
  apiDialect: CredentialApiDialect,
  authStrategy: CredentialAuthStrategy | null,
  apiKeyHeaderName: string,
): string | null {
  if (authStrategy !== "custom_header") {
    return null;
  }
  const normalized = apiKeyHeaderName.trim();
  if (!normalized) {
    return null;
  }
  if (!HTTP_HEADER_TOKEN_PATTERN.test(normalized)) {
    throw new Error("访问密钥请求头名称必须是合法的 HTTP 请求头名称。");
  }
  if (buildRuntimeManagedHeaderNames(apiDialect, "custom_header").has(normalized.toLowerCase())) {
    throw new Error("访问密钥请求头名称不能覆盖系统托管的请求头。");
  }
  return normalized;
}

export function parseExtraHeadersText(
  extraHeadersText: string,
  options?: {
    apiDialect?: CredentialApiDialect;
    authStrategy?: CredentialAuthStrategy | null;
    apiKeyHeaderName?: string | null;
  },
): Record<string, string> | null {
  const normalized = extraHeadersText.trim();
  if (!normalized) {
    return null;
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(normalized);
  } catch {
    throw new Error("额外请求头必须是合法的 JSON 对象。");
  }
  if (parsed === null || Array.isArray(parsed) || typeof parsed !== "object") {
    throw new Error("额外请求头必须是 JSON 对象。");
  }
  const headers: Record<string, string> = {};
  for (const [rawKey, rawValue] of Object.entries(parsed)) {
    const key = rawKey.trim();
    if (!key) {
      throw new Error("额外请求头的键不能为空。");
    }
    if (!HTTP_HEADER_TOKEN_PATTERN.test(key)) {
      throw new Error(`额外请求头 ${key} 不是合法的 HTTP 请求头名称。`);
    }
    if (typeof rawValue !== "string") {
      throw new Error(`额外请求头 ${key} 的值必须是字符串。`);
    }
    const value = rawValue.trim();
    if (!value) {
      throw new Error(`额外请求头 ${key} 的值不能为空。`);
    }
    if (looksLikeSensitiveHeaderName(key)) {
      throw new Error(`额外请求头 ${key} 涉及鉴权或敏感信息，请改用鉴权方式或专用连接字段。`);
    }
    headers[key] = value;
  }
  validateRuntimeManagedHeaderConflicts(headers, options);
  return Object.keys(headers).length > 0 ? headers : null;
}

export function formatExtraHeaders(extraHeaders: Record<string, string> | null): string {
  if (!extraHeaders || Object.keys(extraHeaders).length === 0) {
    return "";
  }
  return JSON.stringify(extraHeaders, null, 2);
}

export function areHeaderMapsEqual(
  left: Record<string, string> | null,
  right: Record<string, string> | null,
): boolean {
  if (left === right) {
    return true;
  }
  if (!left || !right) {
    return left === right;
  }
  const leftKeys = Object.keys(left);
  const rightKeys = Object.keys(right);
  if (leftKeys.length !== rightKeys.length) {
    return false;
  }
  return leftKeys.every((key) => left[key] === right[key]);
}

function validateRuntimeManagedHeaderConflicts(
  headers: Record<string, string>,
  options:
    | {
        apiDialect?: CredentialApiDialect;
        authStrategy?: CredentialAuthStrategy | null;
        apiKeyHeaderName?: string | null;
      }
    | undefined,
) {
  if (!options?.apiDialect) {
    return;
  }
  const reservedHeaders = buildRuntimeManagedHeaderNames(
    options.apiDialect,
    options.authStrategy,
    options.apiKeyHeaderName,
  );
  const conflictingHeaders = Object.keys(headers).filter((headerName) =>
    reservedHeaders.has(headerName.toLowerCase()),
  );
  if (conflictingHeaders.length > 0) {
    throw new Error(`额外请求头不能覆盖系统托管的请求头：${conflictingHeaders.join("、")}。`);
  }
}

function buildRuntimeManagedHeaderNames(
  apiDialect: CredentialApiDialect,
  authStrategy?: CredentialAuthStrategy | null,
  apiKeyHeaderName?: string | null,
): Set<string> {
  const effectiveAuthStrategy = authStrategy ?? getDefaultAuthStrategy(apiDialect);
  const reservedHeaders = new Set<string>([CONTENT_TYPE_HEADER_NAME]);
  if (apiDialect === "anthropic_messages") {
    reservedHeaders.add(ANTHROPIC_VERSION_HEADER_NAME);
  }
  if (effectiveAuthStrategy === "bearer") {
    reservedHeaders.add("authorization");
  }
  if (effectiveAuthStrategy === "x_api_key") {
    reservedHeaders.add("x-api-key");
  }
  if (effectiveAuthStrategy === "x_goog_api_key") {
    reservedHeaders.add("x-goog-api-key");
  }
  if (effectiveAuthStrategy === "custom_header" && apiKeyHeaderName) {
    reservedHeaders.add(apiKeyHeaderName.toLowerCase());
  }
  return reservedHeaders;
}

function looksLikeSensitiveHeaderName(headerName: string): boolean {
  const normalized = headerName.trim().toLowerCase();
  if (SENSITIVE_EXTRA_HEADER_NAMES.has(normalized)) {
    return true;
  }
  return SENSITIVE_EXTRA_HEADER_FRAGMENTS.some((fragment) => normalized.includes(fragment));
}
