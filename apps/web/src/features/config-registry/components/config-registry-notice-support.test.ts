import assert from "node:assert/strict";
import test from "node:test";

import {
  buildConfigRegistrySaveErrorFeedback,
  buildConfigRegistrySaveErrorNotice,
  buildConfigRegistrySaveSuccessNotice,
} from "./config-registry-notice-support";

test("config registry save helpers return success and error states", () => {
  assert.deepEqual(buildConfigRegistrySaveSuccessNotice(), {
    content: "配置已保存。",
    title: "系统配置",
    tone: "success",
  });
  assert.deepEqual(buildConfigRegistrySaveErrorFeedback("  保存失败  "), {
    message: "保存失败",
    tone: "danger",
  });
  assert.deepEqual(buildConfigRegistrySaveErrorNotice("  保存失败  "), {
    content: "保存失败",
    title: "系统配置",
    tone: "danger",
  });
});
