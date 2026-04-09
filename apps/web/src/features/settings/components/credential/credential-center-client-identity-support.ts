import type { CredentialRuntimeKind } from "@/lib/api/types";

export type CredentialRuntimeKindValue = CredentialRuntimeKind | "";

type NormalizedCredentialClientIdentity = {
  clientName: string | null;
  clientVersion: string | null;
  runtimeKind: CredentialRuntimeKind | null;
};

const RUNTIME_KIND_LABELS: Record<CredentialRuntimeKind, string> = {
  "server-python": "服务端 Python",
  "server-node": "服务端 Node",
  browser: "浏览器",
};

const USER_AGENT_RUNTIME_SEGMENTS: Record<CredentialRuntimeKind, string> = {
  "server-python": "server; python",
  "server-node": "server; node",
  browser: "browser",
};

export const RUNTIME_KIND_OPTIONS: Array<{
  value: CredentialRuntimeKindValue;
  label: string;
  description: string;
}> = [
  { value: "", label: "不额外标记", description: "只发送应用名或应用名/版本，不追加运行环境。" },
  { value: "server-python", label: RUNTIME_KIND_LABELS["server-python"], description: "适合 Python 服务端代理。" },
  { value: "server-node", label: RUNTIME_KIND_LABELS["server-node"], description: "适合 Node 服务端代理。" },
  { value: "browser", label: RUNTIME_KIND_LABELS.browser, description: "适合浏览器直连或 Web Runtime。" },
];

export function normalizeCredentialClientIdentity(options: {
  clientName: string;
  clientVersion: string;
  runtimeKind: CredentialRuntimeKindValue;
}): NormalizedCredentialClientIdentity {
  const clientName = normalizeOptionalText(options.clientName);
  const clientVersion = normalizeOptionalText(options.clientVersion);
  const runtimeKind = options.runtimeKind || null;
  if (clientName === null && (clientVersion !== null || runtimeKind !== null)) {
    throw new Error("填写版本或运行环境前，必须先填写应用名。");
  }
  if (clientName === null) {
    return {
      clientName: null,
      clientVersion: null,
      runtimeKind: null,
    };
  }
  return {
    clientName,
    clientVersion,
    runtimeKind,
  };
}

export function buildCredentialUserAgentPreview(options: {
  clientName: string;
  clientVersion: string;
  runtimeKind: CredentialRuntimeKindValue;
}): string | null {
  const normalized = normalizeCredentialClientIdentity(options);
  if (normalized.clientName === null) {
    return null;
  }
  let userAgent = normalized.clientName;
  if (normalized.clientVersion) {
    userAgent = `${userAgent}/${normalized.clientVersion}`;
  }
  if (normalized.runtimeKind) {
    userAgent = `${userAgent} (${USER_AGENT_RUNTIME_SEGMENTS[normalized.runtimeKind]})`;
  }
  return userAgent;
}

function normalizeOptionalText(value: string): string | null {
  const normalized = value.trim();
  return normalized ? normalized : null;
}
