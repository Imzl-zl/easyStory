import { getAuthToken } from "@/lib/stores/auth-store";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export class ApiError extends Error {
  readonly code: string | null;
  readonly detail: unknown;
  readonly status: number;

  constructor(
    message: string,
    status: number,
    detail: unknown,
    code: string | null = null,
  ) {
    super(message);
    this.code = code;
    this.status = status;
    this.detail = detail;
  }
}

export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL;
}

type RequestOptions = {
  body?: unknown;
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  token?: string | null;
};

export async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = options.token ?? getAuthToken();
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: options.method ?? "GET",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    cache: "no-store",
  });

  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    throw createApiErrorFromPayload(payload, response.status);
  }

  return payload as T;
}

export function createApiErrorFromPayload(payload: unknown, status: number): ApiError {
  const detail =
    isRecord(payload) && "detail" in payload
      ? payload.detail
      : payload;
  const code =
    isRecord(payload) && typeof payload.code === "string" && payload.code.trim()
      ? payload.code
      : null;
  return new ApiError(resolveApiMessage(detail, status), status, detail, code);
}

function resolveApiMessage(detail: unknown, status: number): string {
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (Array.isArray(detail) && detail.length > 0) {
    return String(detail[0]);
  }
  return `API request failed with status ${status}`;
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "出现未知错误。";
}

export function getErrorCode(error: unknown): string | null {
  return error instanceof ApiError ? error.code : null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
