import assert from "node:assert/strict";
import test from "node:test";

import { formatObservabilityDateTime } from "./observability-datetime-support";

test("formatObservabilityDateTime renders UTC time consistently", () => {
  assert.equal(formatObservabilityDateTime("2026-03-25T06:08:00Z"), "03/25 06:08 UTC");
  assert.equal(formatObservabilityDateTime("2026-03-25T06:08:00+08:00"), "03/24 22:08 UTC");
  assert.equal(formatObservabilityDateTime(null), "暂无");
});
