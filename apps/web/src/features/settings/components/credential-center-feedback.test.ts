import assert from "node:assert/strict";
import test from "node:test";

import type { CredentialVerifyResult } from "@/lib/api/types";
import { resolveCredentialActionFeedback } from "./credential-center-feedback";

test("resolveCredentialActionFeedback formats verify success time in UTC", () => {
  const result: CredentialVerifyResult = {
    credential_id: "credential-1",
    last_verified_at: "2026-03-25T06:08:00Z",
    message: "验证成功",
    status: "verified",
  };

  assert.deepEqual(resolveCredentialActionFeedback(result, "verify"), {
    message: "验证成功 · 03/25 06:08 UTC",
    tone: "info",
  });
});

test("resolveCredentialActionFeedback keeps non-verify actions semantic and stable", () => {
  assert.deepEqual(resolveCredentialActionFeedback(undefined, "enable"), {
    message: "凭证已启用。",
    tone: "info",
  });
  assert.deepEqual(resolveCredentialActionFeedback(undefined, "disable"), {
    message: "凭证已停用。",
    tone: "info",
  });
  assert.deepEqual(resolveCredentialActionFeedback(undefined, "delete"), {
    message: "凭证已删除。",
    tone: "info",
  });
});
