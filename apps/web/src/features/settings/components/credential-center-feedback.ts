import { getErrorMessage } from "@/lib/api/client";
import type { CredentialVerifyResult, CredentialView } from "@/lib/api/types";
import type { CredentialCenterActionType } from "@/features/settings/components/credential-center-action-support";

export type CredentialCenterFeedback = {
  message: string;
  tone: "info" | "danger";
} | null;

const VERIFY_EMPTY_CONTENT_MARKER = "测试消息没有返回可用内容";
const VERIFY_SUBJECT_PATTERN = /^无法验证\s+(.+?)\s+凭证:\s*/;

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

export function resolveCredentialActionErrorFeedback(error: unknown): CredentialCenterFeedback {
  return {
    message: normalizeCredentialActionErrorMessage(getErrorMessage(error)),
    tone: "danger",
  };
}

export function normalizeCredentialActionErrorMessage(message: string) {
  const trimmed = message.trim();
  if (!trimmed) {
    return "模型连接操作失败，请稍后重试。";
  }
  const subject = resolveVerifySubject(trimmed);
  if (trimmed.includes(VERIFY_EMPTY_CONTENT_MARKER)) {
    return `${subject}验证失败：测试消息没有拿到可用回复。请检查默认模型、接口类型或上游兼容设置。`;
  }
  return trimmed
    .replace(VERIFY_SUBJECT_PATTERN, `${subject}验证失败：`)
    .replaceAll("凭证", "连接");
}

function resolveVerifySubject(message: string) {
  const match = message.match(VERIFY_SUBJECT_PATTERN);
  if (!match?.[1]) {
    return "模型连接";
  }
  return `连接“${match[1].trim()}”`;
}
