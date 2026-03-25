import type { CredentialVerifyResult, CredentialView } from "@/lib/api/types";
import { formatAuditTime } from "@/features/settings/components/credential-center-support";
import type { CredentialCenterActionType } from "@/features/settings/components/credential-center-action-support";

export type CredentialCenterFeedback = {
  message: string;
  tone: "info" | "danger";
} | null;

export function resolveCredentialActionFeedback(
  result: CredentialVerifyResult | CredentialView | void,
  type: CredentialCenterActionType,
): CredentialCenterFeedback {
  if (type === "verify" && result && "message" in result) {
    return {
      message: `${result.message} · ${formatAuditTime(result.last_verified_at)}`,
      tone: "info",
    };
  }
  if (type === "enable") {
    return { message: "凭证已启用。", tone: "info" };
  }
  if (type === "disable") {
    return { message: "凭证已停用。", tone: "info" };
  }
  return { message: "凭证已删除。", tone: "info" };
}
