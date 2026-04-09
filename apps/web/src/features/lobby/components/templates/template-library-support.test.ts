import assert from "node:assert/strict";
import test from "node:test";

import {
  buildTemplateMutationErrorFeedback,
  buildTemplateMutationErrorNotice,
  buildTemplateMutationSuccessNotice,
} from "@/features/lobby/components/templates/template-library-support";

test("template library mutation helpers return user-facing feedback and notices", () => {
  assert.deepEqual(buildTemplateMutationSuccessNotice("create"), {
    content: "模板已创建。",
    title: "模板库",
    tone: "success",
  });
  assert.deepEqual(buildTemplateMutationSuccessNotice("delete"), {
    content: "模板已删除。",
    title: "模板库",
    tone: "success",
  });
  assert.deepEqual(buildTemplateMutationErrorFeedback("  保存失败  "), {
    message: "保存失败",
    tone: "danger",
  });
  assert.deepEqual(buildTemplateMutationErrorNotice("  保存失败  "), {
    content: "保存失败",
    title: "模板库",
    tone: "danger",
  });
});
