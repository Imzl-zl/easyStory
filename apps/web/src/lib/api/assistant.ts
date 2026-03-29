import { getAuthToken } from "@/lib/stores/auth-store";

import { ApiError, getApiBaseUrl, requestJson } from "@/lib/api/client";
import type {
  AssistantPreferences,
  AssistantPreferencesUpdatePayload,
  AssistantRuleProfile,
  AssistantRuleUpdatePayload,
  AssistantTurnPayload,
  AssistantTurnResult,
} from "@/lib/api/types";

type AssistantTurnStreamEvent =
  | { event: "chunk"; data: { delta: string } }
  | { event: "completed"; data: AssistantTurnResult }
  | { event: "error"; data: { message?: string } };

export function runAssistantTurn(payload: AssistantTurnPayload) {
  return requestJson<AssistantTurnResult>("/api/v1/assistant/turn", {
    method: "POST",
    body: payload,
  });
}

export async function runAssistantTurnStream(
  payload: AssistantTurnPayload,
  options: {
    onChunk: (delta: string) => void;
    signal?: AbortSignal;
  },
) {
  const token = getAuthToken();
  const response = await fetch(`${getApiBaseUrl()}/api/v1/assistant/turn`, {
    method: "POST",
    headers: {
      Accept: "text/event-stream",
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ ...payload, stream: true }),
    cache: "no-store",
    signal: options.signal,
  });

  if (!response.ok || !response.body) {
    throw await toAssistantStreamError(response);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let streamedContent = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      buffer += normalizeStreamChunk(decoder.decode());
      const bufferedEvent = parseAssistantTurnStreamEvent(buffer.trim());
      if (bufferedEvent?.event === "chunk" && bufferedEvent.data.delta) {
        options.onChunk(bufferedEvent.data.delta);
        streamedContent += bufferedEvent.data.delta;
        return buildAssistantStreamFallbackResult(payload, streamedContent);
      }
      if (bufferedEvent?.event === "error") {
        throw new Error(bufferedEvent.data.message?.trim() || "实时回复失败，请稍后重试。");
      }
      if (bufferedEvent?.event === "completed") {
        return bufferedEvent.data;
      }
      if (streamedContent.trim()) {
        return buildAssistantStreamFallbackResult(payload, streamedContent);
      }
      throw new Error("实时回复意外中断，请重试。");
    }
    buffer += normalizeStreamChunk(decoder.decode(value, { stream: true }));
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const event = parseAssistantTurnStreamEvent(chunk);
      if (!event) {
        continue;
      }
      if (event.event === "chunk") {
        if (event.data.delta) {
          streamedContent += event.data.delta;
          options.onChunk(event.data.delta);
        }
        continue;
      }
      if (event.event === "error") {
        throw new Error(event.data.message?.trim() || "实时回复失败，请稍后重试。");
      }
      return event.data;
    }
  }
}

export function getMyAssistantPreferences() {
  return requestJson<AssistantPreferences>("/api/v1/assistant/preferences");
}

export function updateMyAssistantPreferences(
  payload: AssistantPreferencesUpdatePayload,
) {
  return requestJson<AssistantPreferences>("/api/v1/assistant/preferences", {
    method: "PUT",
    body: payload,
  });
}

export function getMyAssistantRules() {
  return requestJson<AssistantRuleProfile>("/api/v1/assistant/rules/me");
}

export function updateMyAssistantRules(payload: AssistantRuleUpdatePayload) {
  return requestJson<AssistantRuleProfile>("/api/v1/assistant/rules/me", {
    method: "PUT",
    body: payload,
  });
}

export function getProjectAssistantRules(projectId: string) {
  return requestJson<AssistantRuleProfile>(`/api/v1/assistant/rules/projects/${projectId}`);
}

export function updateProjectAssistantRules(projectId: string, payload: AssistantRuleUpdatePayload) {
  return requestJson<AssistantRuleProfile>(`/api/v1/assistant/rules/projects/${projectId}`, {
    method: "PUT",
    body: payload,
  });
}

function normalizeStreamChunk(value: string) {
  return value.replaceAll("\r\n", "\n").replaceAll("\r", "\n");
}

function parseAssistantTurnStreamEvent(chunk: string): AssistantTurnStreamEvent | null {
  const lines = chunk.split("\n");
  let eventName: string | null = null;
  const dataLines: string[] = [];

  for (const line of lines) {
    if (!line || line.startsWith(":")) {
      continue;
    }
    const separatorIndex = line.indexOf(":");
    if (separatorIndex < 0) {
      continue;
    }
    const field = line.slice(0, separatorIndex);
    const value = line.slice(separatorIndex + 1).trimStart();
    if (field === "event") {
      eventName = value;
      continue;
    }
    if (field === "data") {
      dataLines.push(value);
    }
  }

  if (!eventName || dataLines.length === 0) {
    return null;
  }

  const payload = JSON.parse(dataLines.join("\n")) as unknown;
  if (eventName === "chunk") {
    return { event: "chunk", data: payload as { delta: string } };
  }
  if (eventName === "completed") {
    return { event: "completed", data: payload as AssistantTurnResult };
  }
  if (eventName === "error") {
    return { event: "error", data: payload as { message?: string } };
  }
  return null;
}

async function toAssistantStreamError(response: Response): Promise<Error> {
  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();
  const detail =
    typeof payload === "object" && payload !== null && "detail" in payload
      ? payload.detail
      : payload;
  const message =
    typeof detail === "string" && detail.trim()
      ? detail
      : `实时回复失败，状态码 ${response.status}`;
  return new ApiError(message, response.status, detail);
}

function buildAssistantStreamFallbackResult(
  payload: AssistantTurnPayload,
  content: string,
): AssistantTurnResult {
  return {
    agent_id: payload.agent_id ?? null,
    content,
    hook_results: [],
    input_tokens: null,
    mcp_servers: [],
    model_name: payload.model?.name?.trim() || "",
    output_tokens: null,
    provider: payload.model?.provider?.trim() || "",
    skill_id: payload.skill_id ?? "",
    total_tokens: null,
  };
}
