"use client";

import type {
  AssistantMcpDetail,
  AssistantMcpPayload,
} from "@/lib/api/types";

import {
  assertYamlKeys,
  parseAssistantYamlDocument,
  readOptionalYamlBoolean,
  readOptionalYamlInteger,
  readOptionalYamlObject,
  readOptionalYamlString,
  readRequiredYamlString,
  validateStringRecord,
  type AssistantYamlObject,
} from "./assistant-yaml-document-support";

export const ASSISTANT_MCP_FILE_LABEL = "MCP.yaml";
export const DEFAULT_ASSISTANT_MCP_TIMEOUT = "30";
export const DEFAULT_ASSISTANT_MCP_TRANSPORT = "streamable_http";
export const DEFAULT_ASSISTANT_MCP_VERSION = "1.0.0";

export type AssistantMcpDraft = {
  description: string;
  enabled: boolean;
  headers: Record<string, string>;
  name: string;
  timeout: string;
  transport: string;
  url: string;
  version: string;
};

export function createEmptyAssistantMcpDraft(): AssistantMcpDraft {
  return {
    description: "",
    enabled: true,
    headers: {},
    name: "",
    timeout: DEFAULT_ASSISTANT_MCP_TIMEOUT,
    transport: DEFAULT_ASSISTANT_MCP_TRANSPORT,
    url: "",
    version: DEFAULT_ASSISTANT_MCP_VERSION,
  };
}

export function toAssistantMcpDraft(detail: AssistantMcpDetail): AssistantMcpDraft {
  return {
    description: detail.description ?? "",
    enabled: detail.enabled,
    headers: detail.headers,
    name: detail.name,
    timeout: String(detail.timeout),
    transport: detail.transport,
    url: detail.url,
    version: detail.version,
  };
}

export function buildAssistantMcpPayload(draft: AssistantMcpDraft): AssistantMcpPayload {
  return {
    description: draft.description.trim(),
    enabled: draft.enabled,
    headers: normalizeHeaderMap(draft.headers),
    name: draft.name.trim(),
    timeout: parseAssistantMcpTimeout(draft.timeout),
    transport: draft.transport.trim() || DEFAULT_ASSISTANT_MCP_TRANSPORT,
    url: draft.url.trim(),
    version: draft.version.trim() || DEFAULT_ASSISTANT_MCP_VERSION,
  };
}

export function buildAssistantMcpDocumentPreview(
  draft: AssistantMcpDraft,
  options: { serverId?: string | null } = {},
) {
  const lines = ["mcp_server:"];
  if (options.serverId) {
    lines.push(`  id: ${options.serverId}`);
  }
  lines.push(`  name: ${formatPreviewText(draft.name.trim() || "未命名 MCP")}`);
  lines.push(`  enabled: ${draft.enabled ? "true" : "false"}`);
  lines.push(`  version: ${formatPreviewText(draft.version.trim() || DEFAULT_ASSISTANT_MCP_VERSION)}`);
  if (draft.description.trim()) {
    lines.push(`  description: ${formatPreviewText(draft.description.trim())}`);
  }
  lines.push(`  transport: ${formatPreviewText(draft.transport.trim() || DEFAULT_ASSISTANT_MCP_TRANSPORT)}`);
  lines.push(`  url: ${formatPreviewText(draft.url.trim() || "https://example.com/mcp")}`);
  lines.push(`  headers: ${JSON.stringify(normalizeHeaderMap(draft.headers))}`);
  lines.push(`  timeout: ${parseAssistantMcpTimeout(draft.timeout)}`);
  return lines.join("\n");
}

export function parseAssistantMcpDocument(
  source: string,
  expectedId?: string | null,
): AssistantMcpDraft {
  const document = parseAssistantYamlDocument(source, "mcp_server");
  assertYamlKeys(
    document,
    ["description", "enabled", "headers", "id", "name", "timeout", "transport", "url", "version"],
    "MCP.yaml",
  );
  validateExpectedId(document, expectedId);

  return {
    description: readOptionalYamlString(document, "description", "MCP.yaml description") ?? "",
    enabled: readOptionalYamlBoolean(document, "enabled", "MCP.yaml enabled") ?? true,
    headers: validateStringRecord(
      readOptionalYamlObject(document, "headers", "MCP.yaml headers") ?? {},
      "MCP.yaml headers",
    ),
    name: readRequiredYamlString(document, "name", "MCP.yaml name"),
    timeout: toTimeoutDraft(readOptionalYamlInteger(document, "timeout", "MCP.yaml timeout")),
    transport:
      readOptionalYamlString(document, "transport", "MCP.yaml transport")
      ?? DEFAULT_ASSISTANT_MCP_TRANSPORT,
    url: readRequiredYamlString(document, "url", "MCP.yaml url"),
    version:
      readOptionalYamlString(document, "version", "MCP.yaml version")
      ?? DEFAULT_ASSISTANT_MCP_VERSION,
  };
}

export function isAssistantMcpDirty(
  draft: AssistantMcpDraft,
  detail: AssistantMcpDetail | null,
) {
  if (detail === null) {
    return hasDraftContent(draft);
  }
  return JSON.stringify(draft) !== JSON.stringify(toAssistantMcpDraft(detail));
}

export function buildAssistantMcpListDescription(
  detail: Pick<AssistantMcpDetail, "description" | "enabled" | "transport" | "url">,
) {
  if (!detail.enabled) {
    return "已停用";
  }
  if (detail.description?.trim()) {
    return detail.description.trim();
  }
  return `${resolveAssistantMcpHost(detail.url)} · ${detail.transport}`;
}

export function sanitizeAssistantMcpTimeoutInput(value: string) {
  const digitsOnly = value.replaceAll(/\D/g, "");
  return digitsOnly || DEFAULT_ASSISTANT_MCP_TIMEOUT;
}

export function validateAssistantMcpHeaders(parsed: unknown): {
  errorMessage: string | null;
  value: Record<string, string> | null;
} {
  if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
    return { errorMessage: "需要填写“名称: 内容”的对象格式。", value: null };
  }
  const entries = Object.entries(parsed as Record<string, unknown>);
  if (entries.some(([, value]) => typeof value !== "string")) {
    return { errorMessage: "需要填写“名称: 内容”的对象格式。", value: null };
  }
  return { errorMessage: null, value: parsed as Record<string, string> };
}

function hasDraftContent(draft: AssistantMcpDraft) {
  return Boolean(
    draft.name.trim()
      || draft.description.trim()
      || draft.url.trim()
      || Object.keys(draft.headers).length > 0,
  ) || !draft.enabled || draft.timeout !== DEFAULT_ASSISTANT_MCP_TIMEOUT;
}

function normalizeHeaderMap(value: Record<string, string>) {
  return Object.fromEntries(
    Object.entries(value)
      .map(([key, item]) => [key.trim(), item.trim()])
      .filter(([key, item]) => key && item),
  );
}

function parseAssistantMcpTimeout(value: string) {
  const normalized = value.trim();
  const parsed = Number.parseInt(normalized || DEFAULT_ASSISTANT_MCP_TIMEOUT, 10);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 30;
}

function resolveAssistantMcpHost(url: string) {
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}

function formatPreviewText(value: string) {
  return JSON.stringify(value);
}

function toTimeoutDraft(value: number | null) {
  return value === null ? DEFAULT_ASSISTANT_MCP_TIMEOUT : String(value);
}

function validateExpectedId(document: AssistantYamlObject, expectedId: string | null | undefined) {
  const parsedId = readOptionalYamlString(document, "id", "MCP.yaml id");
  if (expectedId && parsedId && parsedId !== expectedId) {
    throw new Error("MCP 的 id 由系统维护，不能在这里修改。");
  }
}
