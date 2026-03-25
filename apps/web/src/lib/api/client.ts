import { getAuthToken } from "@/lib/stores/auth-store";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export class ApiError extends Error {
  readonly detail: unknown;
  readonly status: number;

  constructor(
    message: string,
    status: number,
    detail: unknown,
  ) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL;
}

type RequestOptions = {
  body?: unknown;
  method?: "GET" | "POST" | "PUT" | "DELETE";
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
    const detail =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? payload.detail
        : payload;
    throw new ApiError(resolveApiMessage(detail, response.status), response.status, detail);
  }

  return payload as T;
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
