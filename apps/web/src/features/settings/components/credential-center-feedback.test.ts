import assert from "node:assert/strict";
import test from "node:test";

import type { CredentialVerifyResult } from "@/lib/api/types";
import { resolveCredentialActionFeedback } from "./credential-center-feedback";

test("resolveCredentialActionFeedback keeps verify success message user-facing", () => {
  const result: CredentialVerifyResult = {
    credential_id: "credential-1",
    last_verified_at: "2026-03-25T06:08:00Z",
    message: "验证成功",
    status: "verified",
  };

  assert.deepEqual(resolveCredentialActionFeedback(result, "verify"), {
    message: "模型连接验证成功。",
    tone: "info",
  });
});

test("resolveCredentialActionFeedback normalizes backend verify success copy to Chinese", () => {
  const result: CredentialVerifyResult = {
    credential_id: "credential-2",
    last_verified_at: "2026-03-27T14:21:00Z",
    message: "Credential verified",
    status: "verified",
  };

  assert.deepEqual(resolveCredentialActionFeedback(result, "verify"), {
    message: "模型连接验证成功。",
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
