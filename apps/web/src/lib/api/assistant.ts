import { getAuthToken } from "@/lib/stores/auth-store";

import { ApiError, createApiErrorFromPayload, getApiBaseUrl, requestJson } from "@/lib/api/client";
import type {
  AssistantAgentDetail,
  AssistantAgentPayload,
  AssistantAgentSummary,
  AssistantHookDetail,
  AssistantHookPayload,
  AssistantHookSummary,
  AssistantPreferences,
  AssistantPreferencesUpdatePayload,
  AssistantRuleProfile,
  AssistantRuleUpdatePayload,
  AssistantTurnPayload,
  AssistantTurnResult,
} from "@/lib/api/types";

export * from "./assistant-mcp";
export * from "./assistant-skills";

type AssistantTurnStreamEventMeta = {
  run_id: string;
  conversation_id: string;
  client_turn_id: string;
  event_seq: number;
  state_version: number;
  ts: string;
};

type AssistantTurnStreamTerminalMeta = {
  runId: string;
  conversationId: string;
  clientTurnId: string;
  eventSeq: number;
  stateVersion: number;
  ts: string;
};

type AssistantTurnRunStartedPayload = AssistantTurnStreamEventMeta & {
  requested_write_scope?: string;
  requested_write_targets?: string[];
};

type AssistantTurnToolCallStartPayload = AssistantTurnStreamEventMeta & {
  tool_call_id: string;
  tool_name: string;
  arguments?: unknown;
  arguments_text?: string;
  target_summary?: unknown;
};

type AssistantTurnToolCallResultPayload = AssistantTurnStreamEventMeta & {
  tool_call_id: string;
  tool_name: string;
  status: string;
  result_summary?: unknown;
  resource_links?: unknown;
  error?: unknown;
};

type AssistantTurnChunkPayload = AssistantTurnStreamEventMeta & {
  delta: string;
};

type AssistantTurnCompletedPayload = AssistantTurnResult & AssistantTurnStreamEventMeta;

type AssistantTurnErrorPayload = AssistantTurnStreamEventMeta & {
  message?: string;
  code?: string;
  terminal_status?: string;
  write_effective?: boolean;
};

type AssistantTurnStreamEvent =
  | {
    event: "run_started";
    data: AssistantTurnRunStartedPayload;
  }
  | {
    event: "tool_call_start";
    data: AssistantTurnToolCallStartPayload;
  }
  | {
    event: "tool_call_result";
    data: AssistantTurnToolCallResultPayload;
  }
  | { event: "chunk"; data: AssistantTurnChunkPayload }
  | { event: "completed"; data: AssistantTurnCompletedPayload }
  | {
    event: "error";
    data: AssistantTurnErrorPayload;
  };

export class AssistantTurnStreamTerminalError extends Error {
  readonly code?: string;
  readonly terminalStatus?: string;
  readonly writeEffective?: boolean;
  readonly runId?: string;
  readonly conversationId?: string;
  readonly clientTurnId?: string;
  readonly eventSeq?: number;
  readonly stateVersion?: number;
  readonly ts?: string;

  constructor(options: {
    message: string;
    code?: string;
    terminalStatus?: string;
    writeEffective?: boolean;
    runId?: string;
    conversationId?: string;
    clientTurnId?: string;
    eventSeq?: number;
    stateVersion?: number;
    ts?: string;
  }) {
    super(options.message);
    this.name = "AssistantTurnStreamTerminalError";
    this.code = options.code;
    this.terminalStatus = options.terminalStatus;
    this.writeEffective = options.writeEffective;
    this.runId = options.runId;
    this.conversationId = options.conversationId;
    this.clientTurnId = options.clientTurnId;
    this.eventSeq = options.eventSeq;
    this.stateVersion = options.stateVersion;
    this.ts = options.ts;
    Object.setPrototypeOf(this, AssistantTurnStreamTerminalError.prototype);
  }
}

export function runAssistantTurn(payload: AssistantTurnPayload) {
  return requestJson<AssistantTurnResult>("/api/v1/assistant/turn", {
    method: "POST",
    body: { ...payload, stream: false },
  });
}

export async function runAssistantTurnStream(
  payload: AssistantTurnPayload,
  options: {
    onChunk: (delta: string) => void;
    signal?: AbortSignal;
  },
) {
  try {
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
    const streamState: AssistantTurnStreamState = {
      cancelledToolMessage: null,
      cancelledToolMeta: null,
      latestEventMeta: null,
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        buffer += normalizeStreamChunk(decoder.decode());
        const completedResult = consumeAssistantTurnStreamChunk(
          buffer.trim(),
          streamState,
          options.onChunk,
        );
        if (completedResult) {
          return completedResult;
        }
        if (streamState.cancelledToolMessage) {
          throw buildCancelledAssistantTurnStreamError(
            streamState.cancelledToolMessage,
            streamState.cancelledToolMeta,
          );
        }
        throw buildInterruptedAssistantTurnStreamError(streamState.latestEventMeta);
      }
      buffer += normalizeStreamChunk(decoder.decode(value, { stream: true }));
      const chunks = buffer.split("\n\n");
      buffer = chunks.pop() ?? "";
      for (const chunk of chunks) {
        const completedResult = consumeAssistantTurnStreamChunk(
          chunk,
          streamState,
          options.onChunk,
        );
        if (completedResult) {
          return completedResult;
        }
      }
    }
  } catch (error) {
    throw normalizeAssistantTurnStreamThrownError(error);
  }
}

type AssistantTurnStreamState = {
  cancelledToolMessage: string | null;
  cancelledToolMeta: AssistantTurnStreamTerminalMeta | null;
  latestEventMeta: AssistantTurnStreamTerminalMeta | null;
};

function consumeAssistantTurnStreamChunk(
  chunk: string,
  streamState: AssistantTurnStreamState,
  onChunk: (delta: string) => void,
) {
  let event: AssistantTurnStreamEvent | null;
  try {
    event = parseAssistantTurnStreamEvent(chunk);
  } catch (error) {
    throw buildInvalidAssistantTurnStreamPayloadError(streamState.latestEventMeta, error);
  }
  return consumeAssistantTurnStreamEvent(
    event,
    streamState,
    onChunk,
  );
}

function consumeAssistantTurnStreamEvent(
  event: AssistantTurnStreamEvent | null,
  streamState: AssistantTurnStreamState,
  onChunk: (delta: string) => void,
): AssistantTurnResult | null {
  if (!event) {
    return null;
  }
  streamState.latestEventMeta = resolveAssistantTurnStreamEventMeta(event);
  if (event.event === "chunk") {
    if (event.data.delta) {
      onChunk(event.data.delta);
    }
    return null;
  }
  if (event.event === "tool_call_result") {
    streamState.cancelledToolMessage = resolveTerminalToolResultMessage(event.data);
    streamState.cancelledToolMeta = resolveTerminalToolResultMeta(event.data);
    return null;
  }
  if (event.event === "error") {
    throw buildAssistantTurnStreamTerminalError(event.data);
  }
  if (event.event === "completed") {
    return event.data;
  }
  return null;
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

export function getProjectAssistantPreferences(projectId: string) {
  return requestJson<AssistantPreferences>(`/api/v1/assistant/preferences/projects/${projectId}`);
}

export function updateProjectAssistantPreferences(
  projectId: string,
  payload: AssistantPreferencesUpdatePayload,
) {
  return requestJson<AssistantPreferences>(`/api/v1/assistant/preferences/projects/${projectId}`, {
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

export function listMyAssistantAgents() {
  return requestJson<AssistantAgentSummary[]>("/api/v1/assistant/agents");
}

export function listMyAssistantHooks() {
  return requestJson<AssistantHookSummary[]>("/api/v1/assistant/hooks");
}

export function createMyAssistantAgent(payload: AssistantAgentPayload) {
  return requestJson<AssistantAgentDetail>("/api/v1/assistant/agents", {
    method: "POST",
    body: payload,
  });
}

export function createMyAssistantHook(payload: AssistantHookPayload) {
  return requestJson<AssistantHookDetail>("/api/v1/assistant/hooks", {
    method: "POST",
    body: payload,
  });
}

export function getMyAssistantAgent(agentId: string) {
  return requestJson<AssistantAgentDetail>(`/api/v1/assistant/agents/${agentId}`);
}

export function getMyAssistantHook(hookId: string) {
  return requestJson<AssistantHookDetail>(`/api/v1/assistant/hooks/${hookId}`);
}

export function updateMyAssistantAgent(agentId: string, payload: AssistantAgentPayload) {
  return requestJson<AssistantAgentDetail>(`/api/v1/assistant/agents/${agentId}`, {
    method: "PUT",
    body: payload,
  });
}

export function updateMyAssistantHook(hookId: string, payload: AssistantHookPayload) {
  return requestJson<AssistantHookDetail>(`/api/v1/assistant/hooks/${hookId}`, {
    method: "PUT",
    body: payload,
  });
}

export function deleteMyAssistantAgent(agentId: string) {
  return requestJson<void>(`/api/v1/assistant/agents/${agentId}`, {
    method: "DELETE",
  });
}

export function deleteMyAssistantHook(hookId: string) {
  return requestJson<void>(`/api/v1/assistant/hooks/${hookId}`, {
    method: "DELETE",
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
    return { event: "chunk", data: payload as AssistantTurnChunkPayload };
  }
  if (eventName === "tool_call_start") {
    return {
      event: "tool_call_start",
      data: payload as AssistantTurnToolCallStartPayload,
    };
  }
  if (eventName === "tool_call_result") {
    return {
      event: "tool_call_result",
      data: payload as AssistantTurnToolCallResultPayload,
    };
  }
  if (eventName === "run_started") {
    return {
      event: "run_started",
      data: payload as AssistantTurnRunStartedPayload,
    };
  }
  if (eventName === "completed") {
    return { event: "completed", data: payload as AssistantTurnCompletedPayload };
  }
  if (eventName === "error") {
    return {
      event: "error",
      data: payload as AssistantTurnErrorPayload,
    };
  }
  return null;
}

function resolveTerminalToolResultMessage(
  payload: AssistantTurnToolCallResultPayload,
): string | null {
  if (payload.status !== "cancelled") {
    return null;
  }
  const resultSummary = payload.result_summary;
  if (
    resultSummary &&
    typeof resultSummary === "object" &&
    "message" in resultSummary &&
    typeof resultSummary.message === "string" &&
    resultSummary.message.trim()
  ) {
    return resultSummary.message.trim();
  }
  return "本轮已停止，当前工具未执行。";
}

function resolveTerminalToolResultMeta(
  payload: AssistantTurnToolCallResultPayload,
): AssistantTurnStreamTerminalMeta | null {
  if (payload.status !== "cancelled") {
    return null;
  }
  return toAssistantTurnStreamTerminalMeta(payload);
}

function toAssistantTurnStreamTerminalMeta(
  payload: AssistantTurnStreamEventMeta,
): AssistantTurnStreamTerminalMeta {
  return {
    runId: payload.run_id,
    conversationId: payload.conversation_id,
    clientTurnId: payload.client_turn_id,
    eventSeq: payload.event_seq,
    stateVersion: payload.state_version,
    ts: payload.ts,
  };
}

function buildAssistantTurnStreamTerminalError(
  payload: AssistantTurnErrorPayload,
) {
  return new AssistantTurnStreamTerminalError({
    message: payload.message?.trim() || "实时回复失败，请稍后重试。",
    code: payload.code,
    terminalStatus: payload.terminal_status,
    writeEffective: payload.write_effective,
    ...toAssistantTurnStreamTerminalMeta(payload),
  });
}

function buildCancelledAssistantTurnStreamError(
  message?: string,
  meta?: AssistantTurnStreamTerminalMeta | null,
) {
  return new AssistantTurnStreamTerminalError({
    message: message?.trim() || "本轮已停止。",
    code: "cancel_requested",
    terminalStatus: "cancelled",
    writeEffective: false,
    ...(meta ?? {}),
  });
}

function buildInterruptedAssistantTurnStreamError(
  meta?: AssistantTurnStreamTerminalMeta | null,
) {
  return new AssistantTurnStreamTerminalError({
    message: "实时回复意外中断，请重试。",
    code: "stream_interrupted",
    terminalStatus: "failed",
    ...(meta ?? {}),
  });
}

function buildInvalidAssistantTurnStreamPayloadError(
  meta?: AssistantTurnStreamTerminalMeta | null,
  cause?: unknown,
) {
  const error = new AssistantTurnStreamTerminalError({
    message: "实时回复数据异常，请重试。",
    code: "stream_payload_invalid",
    terminalStatus: "failed",
    ...(meta ?? {}),
  });
  if (cause !== undefined) {
    error.cause = cause;
  }
  return error;
}

function normalizeAssistantTurnStreamThrownError(error: unknown): Error {
  if (error instanceof AssistantTurnStreamTerminalError) {
    return error;
  }
  if (isAbortError(error)) {
    return buildCancelledAssistantTurnStreamError();
  }
  if (error instanceof Error) {
    return error;
  }
  return new Error("实时回复失败，请稍后重试。");
}

function resolveAssistantTurnStreamEventMeta(
  event: AssistantTurnStreamEvent,
): AssistantTurnStreamTerminalMeta | null {
  if (event.event === "completed" || event.event === "error") {
    return toAssistantTurnStreamTerminalMeta(event.data);
  }
  if (event.event === "run_started" || event.event === "tool_call_start" || event.event === "tool_call_result" || event.event === "chunk") {
    return toAssistantTurnStreamTerminalMeta(event.data);
  }
  return null;
}

function isAbortError(error: unknown) {
  return (
    (typeof DOMException !== "undefined" &&
      error instanceof DOMException &&
      error.name === "AbortError") ||
    (typeof error === "object" &&
      error !== null &&
      "name" in error &&
      error.name === "AbortError")
  );
}

async function toAssistantStreamError(response: Response): Promise<Error> {
  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();
  return createApiErrorFromPayload(payload, response.status);
}
