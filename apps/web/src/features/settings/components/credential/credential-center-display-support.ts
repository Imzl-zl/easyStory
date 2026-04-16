import { formatObservabilityDateTime } from "@/features/observability/components/observability-datetime-support";
import { formatCredentialTokenLimit } from "@/features/settings/components/credential/credential-center-token-support";
import type {
  CredentialVerifyProbeKind,
  CredentialVerifyTransportMode,
  CredentialView,
} from "@/lib/api/types";

export type CredentialTransportCapabilityItem = {
  detail: string;
  lastVerifiedAt: string | null;
  summary: string;
  title: string;
  tone: "completed" | "draft" | "ready" | "warning";
};

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

export function buildCredentialTransportCapabilityItem(
  credential: CredentialView,
  transportMode: CredentialVerifyTransportMode,
): CredentialTransportCapabilityItem {
  const title = transportMode === "buffered" ? "非流链路" : "流式链路";
  const verifiedProbeKind = resolveToolVerifiedProbeKind(credential, transportMode);
  const lastVerifiedAt = transportMode === "buffered"
    ? credential.buffered_tool_last_verified_at
    : credential.stream_tool_last_verified_at;
  const descriptor = resolveToolCapabilityDescriptor(verifiedProbeKind);
  return {
    detail: descriptor.detail,
    lastVerifiedAt,
    summary: descriptor.summary,
    title,
    tone: descriptor.tone,
  };
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

type CredentialCapabilityDescriptor = Pick<CredentialTransportCapabilityItem, "detail" | "summary" | "tone">;

function resolveToolCapabilityDescriptor(
  verifiedProbeKind: CredentialVerifyProbeKind | null | undefined,
): CredentialCapabilityDescriptor {
  if (verifiedProbeKind === "tool_continuation_probe") {
    return {
      detail: "这条链路已经通过完整工具续接验证，可直接承接项目工具。",
      summary: "工具链已就绪",
      tone: "completed",
    };
  }
  if (verifiedProbeKind === "tool_call_probe") {
    return {
      detail: "模型已经能发起工具调用，最后一步还没验证工具结果续接。",
      summary: "工具调用已通",
      tone: "warning",
    };
  }
  if (verifiedProbeKind === "tool_definition_probe") {
    return {
      detail: "模型接受工具定义，但还没确认它会按约定调用工具。",
      summary: "工具定义已通",
      tone: "ready",
    };
  }
  if (verifiedProbeKind === "text_probe") {
    return {
      detail: "这条链路已经确认能稳定返回文本，工具能力还没验证。",
      summary: "基础连接可用",
      tone: "ready",
    };
  }
  return {
    detail: "还没执行这条链路的验证。",
    summary: "未验证",
    tone: "draft",
  };
}
