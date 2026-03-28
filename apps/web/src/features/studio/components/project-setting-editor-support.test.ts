import assert from "node:assert/strict";
import test from "node:test";

import { EMPTY_SETTING, isProjectSettingDirty } from "./project-setting-editor-support";

test("isProjectSettingDirty only reports true when project setting actually changes", () => {
  assert.equal(isProjectSettingDirty(EMPTY_SETTING, EMPTY_SETTING), false);
  assert.equal(
    isProjectSettingDirty(
      { ...EMPTY_SETTING, genre: "都市" },
      EMPTY_SETTING,
    ),
    true,
  );
});
