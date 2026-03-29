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
