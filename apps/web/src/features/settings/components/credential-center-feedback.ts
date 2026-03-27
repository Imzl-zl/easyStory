import { getErrorMessage } from "@/lib/api/client";
import { looksLikeRetiredModelMessage, normalizeModelProviderMessage } from "@/lib/api/error-copy";
import type { CredentialVerifyResult, CredentialView } from "@/lib/api/types";
import type { CredentialCenterActionType } from "@/features/settings/components/credential-center-action-support";

export type CredentialCenterFeedback = {
  message: string;
  tone: "info" | "danger";
} | null;

const VERIFY_MISMATCH_MARKER = "验证响应不匹配";
const VERIFY_ACTUAL_PATTERN = /实际“([\s\S]+)”[。.]?$/;
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
  const actualMessage = extractVerifyActualMessage(trimmed);
  if (trimmed.includes(VERIFY_MISMATCH_MARKER)) {
    return buildVerifyMismatchMessage(subject, actualMessage);
  }
  return trimmed
    .replace(VERIFY_SUBJECT_PATTERN, `${subject}验证失败：`)
    .replaceAll("凭证", "连接");
}

function buildVerifyMismatchMessage(subject: string, actualMessage: string | null) {
  if (!actualMessage) {
    return `${subject}验证失败：模型连接已打通，但返回内容不符合验证要求。请检查默认模型、接口类型或上游兼容设置。`;
  }
  if (looksLikeRetiredModelMessage(actualMessage)) {
    return `${subject}验证失败：${normalizeModelProviderMessage(actualMessage)}`;
  }
  return `${subject}验证失败：模型连接已打通，但返回内容不符合验证要求。请检查默认模型、接口类型或上游兼容设置。上游返回：${actualMessage}`;
}

function extractVerifyActualMessage(message: string) {
  const match = message.match(VERIFY_ACTUAL_PATTERN);
  return match?.[1]?.trim() || null;
}

function resolveVerifySubject(message: string) {
  const match = message.match(VERIFY_SUBJECT_PATTERN);
  if (!match?.[1]) {
    return "模型连接";
  }
  return `连接“${match[1].trim()}”`;
}
