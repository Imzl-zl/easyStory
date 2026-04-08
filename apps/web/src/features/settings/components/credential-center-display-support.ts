import { formatObservabilityDateTime } from "@/features/observability/components/observability-datetime-support";
import { formatCredentialTokenLimit } from "@/features/settings/components/credential-center-token-support";
import type { CredentialView } from "@/lib/api/types";

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

export function formatCredentialToolCapabilitySummary(credential: CredentialView) {
  if (credential.verified_probe_kind === "tool_continuation_probe") {
    return "工具能力：已验证完整工具调用";
  }
  if (credential.verified_probe_kind === "tool_call_probe") {
    return "工具能力：已验证工具调用，未验证结果续接";
  }
  if (credential.verified_probe_kind === "tool_definition_probe") {
    return "工具能力：仅验证工具定义";
  }
  if (credential.verified_probe_kind === "text_probe") {
    return "工具能力：仅验证基础连接";
  }
  return "工具能力：未验证";
}
