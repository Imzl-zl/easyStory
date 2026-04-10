import assert from "node:assert/strict";
import test from "node:test";

import {
  buildProjectSettingSummarySourceExcerpt,
  normalizeProjectSettingSummarySourceContent,
} from "@/features/project-settings/components/project-setting-summary-editor-support";

test("normalizeProjectSettingSummarySourceContent trims surrounding whitespace", () => {
  assert.equal(
    normalizeProjectSettingSummarySourceContent("\n  项目说明正文  \n"),
    "项目说明正文",
  );
});

test("buildProjectSettingSummarySourceExcerpt collapses whitespace and truncates long text", () => {
  assert.equal(
    buildProjectSettingSummarySourceExcerpt("第一行\n\n第二行\t第三行", 20),
    "第一行 第二行 第三行",
  );
  assert.equal(
    buildProjectSettingSummarySourceExcerpt("a".repeat(25), 20),
    `${"a".repeat(20)}…`,
  );
});
