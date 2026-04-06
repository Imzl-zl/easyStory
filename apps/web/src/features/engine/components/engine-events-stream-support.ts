"use client";

import { ApiError, createApiErrorFromPayload, getApiBaseUrl } from "@/lib/api/client";
import type { ExecutionLogView } from "@/lib/api/types";

const STREAM_TIMEOUT_SECONDS = 300;
const STREAM_POLL_INTERVAL_MS = 500;
const MAX_LOCAL_LOGS = 200;

type WorkflowEventsOutcome = "closed" | "ended";

type ParsedWorkflowEvent =
  | { event: "execution_log"; data: ExecutionLogView }
  | { event: "end"; data: { workflow_id: string } };

export async function consumeWorkflowEvents({
  workflowId,
  token,
  signal,
  onOpen,
  onExecutionLog,
}: {
  workflowId: string;
  token: string;
  signal: AbortSignal;
  onOpen: () => void;
  onExecutionLog: (log: ExecutionLogView) => void;
}): Promise<WorkflowEventsOutcome> {
  const response = await fetch(buildWorkflowEventsUrl(workflowId), {
    method: "GET",
    headers: {
      Accept: "text/event-stream",
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
    signal,
  });

  if (!response.ok || !response.body) {
    throw await toStreamError(response);
  }

  onOpen();
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      return "closed";
    }
    buffer += normalizeChunk(decoder.decode(value, { stream: true }));
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const event = parseWorkflowEvent(chunk);
      if (!event) {
        continue;
      }
      if (event.event === "execution_log") {
        onExecutionLog(event.data);
        continue;
      }
      return "ended";
    }
  }
}

export function mergeExecutionLogs(
  snapshotLogs: ExecutionLogView[],
  localLogs: ExecutionLogView[],
): ExecutionLogView[] {
  const mergedById = new Map<string, ExecutionLogView>();
  [...snapshotLogs, ...localLogs].forEach((log) => {
    mergedById.set(log.id, log);
  });
  return Array.from(mergedById.values()).sort(compareLogs);
}

export function upsertExecutionLog(
  logs: ExecutionLogView[],
  nextLog: ExecutionLogView,
): ExecutionLogView[] {
  const filtered = logs.filter((log) => log.id !== nextLog.id);
  return [nextLog, ...filtered].sort(compareLogs).slice(0, MAX_LOCAL_LOGS);
}

export function buildSystemExecutionLog(
  workflowId: string,
  message: string,
): ExecutionLogView {
  return {
    id: `system-${Date.now()}`,
    workflow_execution_id: workflowId,
    node_execution_id: null,
    level: "INFO",
    message,
    details: { source: "engine_sse", type: "system_event" },
    created_at: new Date().toISOString(),
  };
}

export function isClientStreamError(error: unknown): boolean {
  return error instanceof ApiError && error.status >= 400 && error.status < 500;
}

export function resolveClientStreamErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.message.trim()) {
    return `实时连接失败：${error.message}`;
  }
  return "实时连接失败，请刷新页面后重试。";
}

function buildWorkflowEventsUrl(workflowId: string): string {
  const search = new URLSearchParams({
    timeout_seconds: String(STREAM_TIMEOUT_SECONDS),
    poll_interval_ms: String(STREAM_POLL_INTERVAL_MS),
  });
  return `${getApiBaseUrl()}/api/v1/workflows/${workflowId}/events?${search.toString()}`;
}

function normalizeChunk(value: string): string {
  return value.replaceAll("\r\n", "\n").replaceAll("\r", "\n");
}

function parseWorkflowEvent(chunk: string): ParsedWorkflowEvent | null {
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
  if (eventName === "execution_log") {
    return { event: "execution_log", data: payload as ExecutionLogView };
  }
  if (eventName === "end" && typeof payload === "object" && payload !== null) {
    return { event: "end", data: payload as { workflow_id: string } };
  }
  return null;
}

function compareLogs(left: ExecutionLogView, right: ExecutionLogView): number {
  return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
}

async function toStreamError(response: Response): Promise<Error> {
  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();
  return createApiErrorFromPayload(payload, response.status);
}
