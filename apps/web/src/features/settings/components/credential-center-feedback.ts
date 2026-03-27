import type { CredentialVerifyResult, CredentialView } from "@/lib/api/types";
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
      message: "模型连接验证成功。",
      tone: "info",
    };
  }
  if (type === "enable") {
    return { message: "模型连接已启用。", tone: "info" };
  }
  if (type === "disable") {
    return { message: "模型连接已停用。", tone: "info" };
  }
  return { message: "模型连接已删除。", tone: "info" };
}
