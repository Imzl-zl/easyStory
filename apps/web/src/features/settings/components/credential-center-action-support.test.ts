import assert from "node:assert/strict";
import test from "node:test";

import {
  isPendingCredentialAction,
  resolveCredentialActionButtonLabel,
  resolvePendingCredentialAction,
  type PendingCredentialAction,
} from "./credential-center-action-support";

test("resolvePendingCredentialAction returns current action only while mutation is pending", () => {
  const pendingAction: PendingCredentialAction = {
    credentialId: "credential-1",
    type: "verify_connection",
  };

  assert.equal(resolvePendingCredentialAction(false, pendingAction), null);
  assert.equal(resolvePendingCredentialAction(true, undefined), null);
  assert.deepEqual(resolvePendingCredentialAction(true, pendingAction), pendingAction);
});

test("isPendingCredentialAction matches current row and action type", () => {
  const pendingAction: PendingCredentialAction = {
    credentialId: "credential-1",
    type: "disable",
  };

  assert.equal(isPendingCredentialAction(pendingAction, "disable", "credential-1"), true);
  assert.equal(isPendingCredentialAction(pendingAction, "enable", "credential-1"), false);
  assert.equal(isPendingCredentialAction(pendingAction, "disable", "credential-2"), false);
});

test("resolveCredentialActionButtonLabel returns explicit pending labels", () => {
  assert.equal(resolveCredentialActionButtonLabel("verify_connection", false), "验证连接");
  assert.equal(resolveCredentialActionButtonLabel("verify_connection", true), "验证中...");
  assert.equal(resolveCredentialActionButtonLabel("verify_tools", false), "验证工具");
  assert.equal(resolveCredentialActionButtonLabel("verify_tools", true), "验证中...");
  assert.equal(resolveCredentialActionButtonLabel("enable", true), "启用中...");
  assert.equal(resolveCredentialActionButtonLabel("disable", true), "停用中...");
  assert.equal(resolveCredentialActionButtonLabel("delete", true), "删除中...");
});
