import { formatObservabilityDateTime } from "@/features/observability/components/observability-datetime-support";
import { formatCredentialTokenLimit } from "@/features/settings/components/credential/credential-center-token-support";
import type {
  CredentialVerifyProbeKind,
  CredentialVerifyTransportMode,
  CredentialView,
} from "@/lib/api/types";

export function formatAuditTime(value: string) {
  return formatObservabilityDateTime(value);
}

export function formatCredentialTokenSummary(credential: CredentialView) {
  const contextWindow = formatCredentialTokenLimit(credential.context_window_tokens);
  const maxOutput = formatCredentialTokenLimit(credential.default_max_output_tokens);
  if (!contextWindow && !maxOutput) {
    return "上下文窗口：未填写 · 回复上限：未填写";
  }
  return `上下文窗口：${contextWindow ?? "未填写"} · 回复上限：${maxOutput ?? "未填写"}`;
}

export function formatCredentialToolCapabilitySummary(
  credential: CredentialView,
  transportMode: CredentialVerifyTransportMode,
) {
  const modeLabel = transportMode === "buffered" ? "非流工具" : "流式工具";
  const verifiedProbeKind = resolveToolVerifiedProbeKind(credential, transportMode);
  const lastVerifiedAt = transportMode === "buffered"
    ? credential.buffered_tool_last_verified_at
    : credential.stream_tool_last_verified_at;
  const summary = resolveToolCapabilityLabel(verifiedProbeKind);
  if (!lastVerifiedAt) {
    return `${modeLabel}：${summary}`;
  }
  return `${modeLabel}：${summary} · 最近验证：${formatAuditTime(lastVerifiedAt)}`;
}

function resolveToolVerifiedProbeKind(
  credential: CredentialView,
  transportMode: CredentialVerifyTransportMode,
): CredentialVerifyProbeKind | null | undefined {
  if (transportMode === "buffered") {
    return credential.buffered_tool_verified_probe_kind;
  }
  return credential.stream_tool_verified_probe_kind;
}

function resolveToolCapabilityLabel(
  verifiedProbeKind: CredentialVerifyProbeKind | null | undefined,
) {
  if (verifiedProbeKind === "tool_continuation_probe") {
    return "已验证完整工具调用";
  }
  if (verifiedProbeKind === "tool_call_probe") {
    return "已验证工具调用，未验证结果续接";
  }
  if (verifiedProbeKind === "tool_definition_probe") {
    return "仅验证工具定义";
  }
  if (verifiedProbeKind === "text_probe") {
    return "仅验证基础连接";
  }
  return "未验证";
}
