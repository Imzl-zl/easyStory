import assert from "node:assert/strict";
import test from "node:test";

import {
  ASSISTANT_DEFAULT_CHAT_SKILL_ID,
  ASSISTANT_DEFAULT_CHAT_SKILL_LABEL,
} from "./assistant-defaults";
import { buildAssistantSkillSelectOptions } from "./assistant-skill-select-options";

test("assistant skill select options distinguish system default skill from custom skill with same name", () => {
  assert.deepEqual(
    buildAssistantSkillSelectOptions(
      [{ enabled: true, id: "skill.user.story-helper-a1b2c3", name: ASSISTANT_DEFAULT_CHAT_SKILL_LABEL }],
      { defaultDescription: "系统内置", includeSystemDefault: true },
    ),
    [
      {
        description: "系统内置",
        label: "默认聊天助手（系统）",
        value: ASSISTANT_DEFAULT_CHAT_SKILL_ID,
      },
      {
        description: "你自己创建的 Skill",
        label: "默认聊天助手（自定义）",
        value: "skill.user.story-helper-a1b2c3",
      },
    ],
  );
});

test("assistant skill select options can keep disabled skills visible for editor scenes", () => {
  assert.deepEqual(
    buildAssistantSkillSelectOptions(
      [{ enabled: false, id: "skill.user.story-helper-a1b2c3", name: "温柔陪跑" }],
      {
        defaultDescription: "系统内置",
        disabledDescription: "已停用，但 Agent 仍可继续绑定使用",
        includeDisabled: true,
        includeSystemDefault: true,
      },
    ),
    [
      {
        description: "系统内置",
        label: ASSISTANT_DEFAULT_CHAT_SKILL_LABEL,
        value: ASSISTANT_DEFAULT_CHAT_SKILL_ID,
      },
      {
        description: "已停用，但 Agent 仍可继续绑定使用",
        label: "温柔陪跑（已停用）",
        value: "skill.user.story-helper-a1b2c3",
      },
    ],
  );
});

test("assistant skill select options can start from explicit no-skill option without injecting system default", () => {
  assert.deepEqual(
    buildAssistantSkillSelectOptions(
      [{ enabled: true, id: "skill.user.story-helper-a1b2c3", name: "温柔陪跑" }],
      {
        leadingOptions: [{ label: "不额外套用 Skill", value: "" }],
      },
    ),
    [
      { label: "不额外套用 Skill", value: "" },
      { description: undefined, label: "温柔陪跑", value: "skill.user.story-helper-a1b2c3" },
    ],
  );
});
