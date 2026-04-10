import assert from "node:assert/strict";
import test from "node:test";

import {
  buildProjectSettingIssueSummary,
} from "@/features/project/components/project-setting-summary-support";

test("buildProjectSettingIssueSummary falls back to empty message when there are no issues", () => {
  assert.equal(
    buildProjectSettingIssueSummary({ issues: [], status: "ready" }, "当前摘要已完整。"),
    "当前摘要已完整。",
  );
});
