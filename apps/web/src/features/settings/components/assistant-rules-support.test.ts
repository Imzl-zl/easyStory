import assert from "node:assert/strict";
import test from "node:test";

import {
  buildAssistantRuleFieldId,
  buildAssistantRuleFormKey,
  isAssistantRuleDirty,
  toAssistantRuleDraft,
} from "./assistant-rules-support";

const profile = {
  content: "先给结论。",
  enabled: true,
  scope: "user",
  updated_at: "2026-03-28T12:00:00Z",
} as const;

test("assistant rules support builds editable draft and stable form key", () => {
  assert.deepEqual(toAssistantRuleDraft(profile), {
    content: "先给结论。",
    enabled: true,
  });
  assert.equal(buildAssistantRuleFormKey(profile), "user:2026-03-28T12:00:00Z:true:先给结论。");
  assert.equal(buildAssistantRuleFieldId("project"), "project-assistant-rules");
});

test("assistant rules support detects dirty state", () => {
  assert.equal(isAssistantRuleDirty({ content: "先给结论。", enabled: true }, profile), false);
  assert.equal(isAssistantRuleDirty({ content: "直接给方案。", enabled: true }, profile), true);
  assert.equal(isAssistantRuleDirty({ content: "先给结论。", enabled: false }, profile), true);
});
