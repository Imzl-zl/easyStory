import assert from "node:assert/strict";
import test from "node:test";

import type { CredentialVerifyResult } from "@/lib/api/types";
import {
  normalizeCredentialActionErrorMessage,
  resolveCredentialActionFeedback,
} from "./credential-center-feedback";

test("resolveCredentialActionFeedback keeps verify success message user-facing", () => {
  const result: CredentialVerifyResult = {
    credential_id: "credential-1",
    last_verified_at: "2026-03-25T06:08:00Z",
    message: "验证成功",
    probe_kind: "text_probe",
    status: "verified",
  };

  assert.deepEqual(resolveCredentialActionFeedback(
    { ...result, transport_mode: "stream", message: "流式连接验证成功" },
    "verify_stream_connection",
  ), {
    message: "流式链路验证成功。",
    tone: "info",
  });
  assert.deepEqual(resolveCredentialActionFeedback(
    { ...result, transport_mode: "buffered", message: "非流连接验证成功" },
    "verify_buffered_connection",
  ), {
    message: "非流链路验证成功。",
    tone: "info",
  });
});

test("resolveCredentialActionFeedback normalizes backend verify success copy to Chinese", () => {
  const result: CredentialVerifyResult = {
    credential_id: "credential-2",
    last_verified_at: "2026-03-27T14:21:00Z",
    message: "Credential verified",
    probe_kind: "text_probe",
    status: "verified",
    transport_mode: "stream",
  };

  assert.deepEqual(resolveCredentialActionFeedback(result, "verify_stream_connection"), {
    message: "流式链路验证成功。",
    tone: "info",
  });
});

test("resolveCredentialActionFeedback keeps tool verify success message user-facing", () => {
  const result: CredentialVerifyResult = {
    credential_id: "credential-3",
    last_verified_at: "2026-04-08T09:15:00Z",
    message: "流式工具调用验证成功",
    probe_kind: "tool_continuation_probe",
    status: "verified",
    transport_mode: "stream",
  };

  assert.deepEqual(resolveCredentialActionFeedback(result, "verify_stream_tools"), {
    message: "流式工具验证成功。",
    tone: "info",
  });
  assert.deepEqual(resolveCredentialActionFeedback(
    { ...result, transport_mode: "buffered", message: "非流工具调用验证成功" },
    "verify_buffered_tools",
  ), {
    message: "非流工具验证成功。",
    tone: "info",
  });
});

test("resolveCredentialActionFeedback keeps non-verify actions semantic and stable", () => {
  assert.deepEqual(resolveCredentialActionFeedback(undefined, "enable"), {
    message: "模型连接已启用。",
    tone: "info",
  });
  assert.deepEqual(resolveCredentialActionFeedback(undefined, "disable"), {
    message: "模型连接已停用。",
    tone: "info",
  });
  assert.deepEqual(resolveCredentialActionFeedback(undefined, "delete"), {
    message: "模型连接已删除。",
    tone: "info",
  });
});

test("normalizeCredentialActionErrorMessage rewrites empty probe content into user-facing Chinese", () => {
  assert.equal(
    normalizeCredentialActionErrorMessage(
      "无法验证 薄荷 凭证: 测试消息没有返回可用内容",
      "verify_stream_connection",
    ),
    "连接“薄荷”流式链路验证失败：测试消息没有拿到可用回复。请检查默认模型、接口类型或上游兼容设置。",
  );
});

test("normalizeCredentialActionErrorMessage keeps connection transport labels explicit", () => {
  assert.equal(
    normalizeCredentialActionErrorMessage(
      "无法验证 薄荷 凭证: 流式连接验证失败：HTTP 503 - upstream unavailable",
      "verify_stream_connection",
    ),
    "连接“薄荷”流式链路验证失败：HTTP 503 - upstream unavailable",
  );
  assert.equal(
    normalizeCredentialActionErrorMessage(
      "无法验证 薄荷 凭证: 测试消息没有返回可用内容",
      "verify_buffered_connection",
    ),
    "连接“薄荷”非流链路验证失败：测试消息没有拿到可用回复。请检查默认模型、接口类型或上游兼容设置。",
  );
});

test("normalizeCredentialActionErrorMessage keeps backend normalized upstream errors readable", () => {
  assert.equal(
    normalizeCredentialActionErrorMessage(
      "无法验证 OpenAI 凭证: 当前默认模型已不可用，请换成可用模型后再试。上游提示：Gemini 3 Pro is no longer available. Please switch to Gemini 3.1 Pro.",
      "verify_stream_connection",
    ),
    "连接“OpenAI”流式链路验证失败：当前默认模型已不可用，请换成可用模型后再试。上游提示：Gemini 3 Pro is no longer available. Please switch to Gemini 3.1 Pro.",
  );
});

test("normalizeCredentialActionErrorMessage rewrites tool call probe failure into user-facing Chinese", () => {
  assert.equal(
    normalizeCredentialActionErrorMessage(
      "无法验证 bwen 凭证: 流式工具调用验证失败：Tool call probe expected exactly one tool call, got 0",
      "verify_stream_tools",
    ),
    "连接“bwen”流式工具调用验证失败：模型没有按约定发起工具调用。请检查接口类型、兼容 Profile 或上游工具调用支持。",
  );
});

test("normalizeCredentialActionErrorMessage rewrites tool continuation dynamic echo failure into user-facing Chinese", () => {
  assert.equal(
    normalizeCredentialActionErrorMessage(
      "无法验证 bwen 凭证: 非流工具调用验证失败：Tool continuation probe final content must mention 'probe-result-123'",
      "verify_buffered_tools",
    ),
    "连接“bwen”非流工具调用验证失败：模型没有完成工具结果续接。请检查上游的 tool continuation 兼容性。",
  );
});
