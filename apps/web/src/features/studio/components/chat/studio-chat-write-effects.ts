"use client";

import type { AssistantTurnResult } from "@/lib/api/types";

export type StudioAssistantWriteEffectStatus =
  | "started"
  | "completed"
  | "committed"
  | "errored"
  | "failed"
  | "cancelled";

export type StudioAssistantWriteEffect = {
  paths: string[];
  status: StudioAssistantWriteEffectStatus;
  toolCallId: string | null;
};

type StudioToolCallStartPayload = {
  target_summary?: unknown;
  tool_call_id: string;
  tool_name: string;
};

type StudioToolCallResultPayload = {
  result_summary?: unknown;
  status: string;
  tool_call_id: string;
  tool_name: string;
};

export function resolveStudioWriteEffectFromToolCallStart(
  payload: StudioToolCallStartPayload,
): StudioAssistantWriteEffect | null {
  if (payload.tool_name !== "project.write_document") {
    return null;
  }
  const paths = readStudioAssistantWritePaths(payload.target_summary);
  return {
    paths,
    status: "started",
    toolCallId: payload.tool_call_id,
  };
}

export function resolveStudioWriteEffectFromToolCallResult(
  payload: StudioToolCallResultPayload,
  fallbackPaths: readonly string[] = [],
): StudioAssistantWriteEffect | null {
  if (payload.tool_name !== "project.write_document") {
    return null;
  }
  const status = normalizeStudioAssistantWriteStatus(payload.status);
  if (status === null) {
    return null;
  }
  const paths = readStudioAssistantWritePaths(payload.result_summary);
  return {
    paths: paths.length > 0 ? paths : [...fallbackPaths],
    status,
    toolCallId: payload.tool_call_id,
  };
}

export function collectStudioWriteEffectsFromTurnResult(
  result: AssistantTurnResult,
): StudioAssistantWriteEffect[] {
  return result.output_items.flatMap((item) => {
    if (item.item_type !== "tool_result") {
      return [];
    }
    const toolName = readStudioToolName(item);
    if (toolName !== "project.write_document") {
      return [];
    }
    const status = normalizeStudioAssistantWriteStatus(
      typeof item.status === "string" ? item.status : null,
    );
    if (status === null) {
      return [];
    }
    return [{
      paths: readStudioAssistantWritePaths(item.payload),
      status,
      toolCallId: typeof item.call_id === "string" ? item.call_id : null,
    }];
  });
}

export function isStudioAssistantWriteSuccessStatus(
  status: StudioAssistantWriteEffectStatus,
) {
  return status === "completed" || status === "committed";
}

function normalizeStudioAssistantWriteStatus(
  status: string | null | undefined,
): StudioAssistantWriteEffectStatus | null {
  if (
    status === "completed"
    || status === "committed"
    || status === "errored"
    || status === "failed"
    || status === "cancelled"
  ) {
    return status;
  }
  return null;
}

function readStudioToolName(item: AssistantTurnResult["output_items"][number]) {
  if ("tool_name" in item && typeof item.tool_name === "string") {
    return item.tool_name;
  }
  if (
    item.payload &&
    typeof item.payload === "object"
    && "tool_name" in item.payload
    && typeof item.payload.tool_name === "string"
  ) {
    return item.payload.tool_name;
  }
  return null;
}

function readStudioAssistantWritePaths(value: unknown) {
  const pathSet = new Set<string>();
  collectStudioAssistantWritePaths(pathSet, value);
  return [...pathSet];
}

function collectStudioAssistantWritePaths(
  pathSet: Set<string>,
  value: unknown,
) {
  if (!value || typeof value !== "object") {
    return;
  }
  if ("path" in value && typeof value.path === "string" && value.path.trim()) {
    pathSet.add(value.path.trim());
  }
  if ("paths" in value && Array.isArray(value.paths)) {
    value.paths.forEach((item) => {
      if (typeof item === "string" && item.trim()) {
        pathSet.add(item.trim());
      }
    });
  }
  if ("structured_output" in value) {
    collectStudioAssistantWritePaths(pathSet, value.structured_output);
  }
  if ("resource_links" in value && Array.isArray(value.resource_links)) {
    value.resource_links.forEach((item) => collectStudioAssistantWritePaths(pathSet, item));
  }
  if ("documents" in value && Array.isArray(value.documents)) {
    value.documents.forEach((item) => collectStudioAssistantWritePaths(pathSet, item));
  }
}
