import assert from "node:assert/strict";
import test from "node:test";

import { formatEngineDateTime } from "./engine-datetime-format";

test("formatEngineDateTime renders true UTC time instead of local timezone", () => {
  assert.equal(formatEngineDateTime("2026-03-25T06:08:00Z"), "03/25 06:08 UTC");
  assert.equal(formatEngineDateTime("2026-03-25T06:08:00+08:00"), "03/24 22:08 UTC");
  assert.equal(formatEngineDateTime(null), "暂无");
});
