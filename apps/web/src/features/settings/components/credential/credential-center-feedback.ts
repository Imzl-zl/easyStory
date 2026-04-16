import { getErrorMessage } from "@/lib/api/client";
import type { CredentialVerifyResult, CredentialView } from "@/lib/api/types";
import type { CredentialCenterActionType } from "@/features/settings/components/credential/credential-center-action-support";

export type CredentialCenterFeedback = {
  message: string;
  tone: "info" | "danger";
} | null;

const VERIFY_EMPTY_CONTENT_MARKER = "测试消息没有返回可用内容";
const VERIFY_SUBJECT_PATTERN = /^无法验证\s+(.+?)\s+凭证:\s*/;
const TOOL_CALL_PROBE_ZERO_CALLS_MARKER = "Tool call probe expected exactly one tool call, got 0";
const TOOL_CALL_PROBE_RESPONSE_ID_MARKER = "requires provider_response_id";
const TOOL_CONTINUATION_EMPTY_MARKER = "Tool continuation probe returned empty final content";
const TOOL_CONTINUATION_EQUAL_MARKER = "Tool continuation probe final content must equal";
const TOOL_CONTINUATION_FOLLOWUP_MARKER = "Tool continuation probe final content must mention";

export function resolveCredentialActionFeedback(
  result: CredentialVerifyResult | CredentialView | void,
  type: CredentialCenterActionType,
): CredentialCenterFeedback {
  if (type === "verify_stream_connection" && result && "message" in result) {
    return {
      message: "流式链路验证成功。",
      tone: "info",
    };
  }
  if (type === "verify_buffered_connection" && result && "message" in result) {
    return {
      message: "非流链路验证成功。",
      tone: "info",
    };
  }
  if (type === "verify_stream_tools" && result && "message" in result) {
    return {
      message: "流式工具验证成功。",
      tone: "info",
    };
  }
  if (type === "verify_buffered_tools" && result && "message" in result) {
    return {
      message: "非流工具验证成功。",
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

export function resolveCredentialActionErrorFeedback(
  error: unknown,
  actionType: CredentialCenterActionType,
): CredentialCenterFeedback {
  return {
    message: normalizeCredentialActionErrorMessage(
      getErrorMessage(error),
      actionType,
    ),
    tone: "danger",
  };
}

export function normalizeCredentialActionErrorMessage(
  message: string,
  actionType: CredentialCenterActionType = "verify_stream_connection",
) {
  const trimmed = message.trim();
  if (!trimmed) {
    return "模型连接操作失败，请稍后重试。";
  }
  if (actionType === "verify_stream_tools") {
    return normalizeToolVerificationErrorMessage(trimmed, "流式工具");
  }
  if (actionType === "verify_buffered_tools") {
    return normalizeToolVerificationErrorMessage(trimmed, "非流工具");
  }
  if (actionType === "verify_stream_connection") {
    return normalizeConnectionVerificationErrorMessage(trimmed, "流式链路");
  }
  if (actionType === "verify_buffered_connection") {
    return normalizeConnectionVerificationErrorMessage(trimmed, "非流链路");
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

function normalizeConnectionVerificationErrorMessage(
  message: string,
  connectionLabel: "流式链路" | "非流链路",
) {
  const subject = resolveVerifySubject(message);
  const legacyLabel = connectionLabel === "流式链路" ? "流式连接" : "非流连接";
  if (message.includes(VERIFY_EMPTY_CONTENT_MARKER)) {
    return `${subject}${connectionLabel}验证失败：测试消息没有拿到可用回复。请检查默认模型、接口类型或上游兼容设置。`;
  }
  return message
    .replace(VERIFY_SUBJECT_PATTERN, `${subject}${connectionLabel}验证失败：`)
    .replace(`${connectionLabel}验证失败：${connectionLabel}验证失败：`, `${connectionLabel}验证失败：`)
    .replace(`${connectionLabel}验证失败：${legacyLabel}验证失败：`, `${connectionLabel}验证失败：`)
    .replaceAll("凭证", "连接");
}

function normalizeToolVerificationErrorMessage(
  message: string,
  toolLabel: "流式工具" | "非流工具",
) {
  const subject = resolveVerifySubject(message);
  if (message.includes(TOOL_CALL_PROBE_ZERO_CALLS_MARKER)) {
    return `${subject}${toolLabel}调用验证失败：模型没有按约定发起工具调用。请检查接口类型、兼容 Profile 或上游工具调用支持。`;
  }
  if (message.includes(TOOL_CALL_PROBE_RESPONSE_ID_MARKER)) {
    return `${subject}${toolLabel}调用验证失败：上游没有返回可用于续接的响应标识，当前接口不具备稳定的工具续接能力。`;
  }
  if (
    message.includes(TOOL_CONTINUATION_EMPTY_MARKER)
    || message.includes(TOOL_CONTINUATION_FOLLOWUP_MARKER)
    || message.includes(TOOL_CONTINUATION_EQUAL_MARKER)
  ) {
    return `${subject}${toolLabel}调用验证失败：模型没有完成工具结果续接。请检查上游的 tool continuation 兼容性。`;
  }
  return message
    .replace(VERIFY_SUBJECT_PATTERN, `${subject}${toolLabel}调用验证失败：`)
    .replace(`${toolLabel}调用验证失败：${toolLabel}调用验证失败：`, `${toolLabel}调用验证失败：`)
    .replaceAll("凭证", "连接");
}
