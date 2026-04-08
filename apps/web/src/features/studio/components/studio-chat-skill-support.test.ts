import assert from "node:assert/strict";
import test from "node:test";

import {
  buildStudioChatSkillOptions,
  filterStudioChatSkillOptions,
  hasStudioSelectedSkill,
  normalizeStudioSkillId,
  resolveStudioActiveSkillState,
  resolveStudioSkillSendBlockReason,
  resolveStudioSendableSkillSelection,
  resolveStudioUsableSkillSelection,
} from "./studio-chat-skill-support";

test("studio chat skill support merges project skills before user skills and skips duplicates", () => {
  assert.deepEqual(
    buildStudioChatSkillOptions({
      projectSkills: [
        {
          description: "项目内固定语气",
          enabled: true,
          id: "skill.shared.story-helper",
          name: "项目语气",
          updated_at: null,
        },
      ],
      userSkills: [
        {
          description: "全局版本",
          enabled: true,
          id: "skill.shared.story-helper",
          name: "全局语气",
          updated_at: null,
        },
        {
          description: "更温柔一点",
          enabled: true,
          id: "skill.user.warm-helper",
          name: "温柔陪跑",
          updated_at: null,
        },
        {
          description: "已停用",
          enabled: false,
          id: "skill.user.disabled-helper",
          name: "停用 Skill",
          updated_at: null,
        },
      ],
    }),
    [
      {
        description: "项目内固定语气",
        label: "项目语气",
        scope: "project",
        scopeLabel: "项目",
        value: "skill.shared.story-helper",
      },
      {
        description: "更温柔一点",
        label: "温柔陪跑",
        scope: "user",
        scopeLabel: "全局",
        value: "skill.user.warm-helper",
      },
    ],
  );
});

test("studio chat skill support summarizes none, once, and conversation modes clearly", () => {
  const skillOptions = buildStudioChatSkillOptions({
    userSkills: [
      {
        description: "更温柔一点",
        enabled: true,
        id: "skill.user.warm-helper",
        name: "温柔陪跑",
        updated_at: null,
      },
      {
        description: null,
        enabled: true,
        id: "skill.user.cold-helper",
        name: "冷峻推进",
        updated_at: null,
      },
    ],
  });

  assert.deepEqual(
    resolveStudioActiveSkillState({ skillOptions }),
    {
      conversationSkillId: null,
      conversationSkillLabel: null,
      detail: "不额外套用 Skill，只使用规则、文稿上下文和当前会话。",
      headline: "普通对话",
      nextTurnSkillId: null,
      nextTurnSkillLabel: null,
    },
  );
  assert.deepEqual(
    resolveStudioActiveSkillState({
      conversationSkillId: "skill.user.warm-helper",
      nextTurnSkillId: "skill.user.cold-helper",
      skillOptions,
    }),
    {
      conversationSkillId: "skill.user.warm-helper",
      conversationSkillLabel: "温柔陪跑",
      detail: "成功发送后回到当前会话 · 温柔陪跑",
      headline: "本次 · 冷峻推进",
      nextTurnSkillId: "skill.user.cold-helper",
      nextTurnSkillLabel: "冷峻推进",
    },
  );
  assert.deepEqual(
    resolveStudioActiveSkillState({
      conversationSkillId: "skill.user.missing-helper",
      skillOptions,
    }),
    {
      conversationSkillId: "skill.user.missing-helper",
      conversationSkillLabel: null,
      detail: "当前已选 Skill 已失效，请重新选择或切回普通对话。",
      headline: "Skill 已失效",
      nextTurnSkillId: null,
      nextTurnSkillLabel: null,
    },
  );
  assert.deepEqual(
    resolveStudioActiveSkillState({
      conversationSkillId: "skill.user.missing-helper",
      skillsLoading: true,
      skillOptions,
    }),
    {
      conversationSkillId: "skill.user.missing-helper",
      conversationSkillLabel: null,
      detail: "Skill 列表仍在读取，确认完成后才会按当前 Skill 发送。",
      headline: "Skill 待确认",
      nextTurnSkillId: null,
      nextTurnSkillLabel: null,
    },
  );
});

test("studio chat skill support normalizes blank skill ids to null", () => {
  assert.equal(normalizeStudioSkillId(undefined), null);
  assert.equal(normalizeStudioSkillId("  "), null);
  assert.equal(normalizeStudioSkillId(" skill.user.helper "), "skill.user.helper");
  assert.equal(hasStudioSelectedSkill({ conversationSkillId: "  " }), false);
  assert.equal(hasStudioSelectedSkill({ nextTurnSkillId: "skill.user.helper" }), true);
});

test("studio chat skill support keeps unresolved skill ids until lookup is stable", () => {
  const skillOptions = buildStudioChatSkillOptions({
    userSkills: [
      {
        description: "更温柔一点",
        enabled: true,
        id: "skill.user.warm-helper",
        name: "温柔陪跑",
        updated_at: null,
      },
    ],
  });

  assert.deepEqual(
    resolveStudioUsableSkillSelection({
      conversationSkillId: "skill.user.missing-helper",
      nextTurnSkillId: "skill.user.warm-helper",
      skillLookupReady: false,
      skillOptions,
    }),
    {
      conversationSkillId: "skill.user.missing-helper",
      nextTurnSkillId: "skill.user.warm-helper",
    },
  );
  assert.deepEqual(
    resolveStudioUsableSkillSelection({
      conversationSkillId: "skill.user.missing-helper",
      nextTurnSkillId: "skill.user.warm-helper",
      skillLookupReady: true,
      skillOptions,
    }),
    {
      conversationSkillId: null,
      nextTurnSkillId: "skill.user.warm-helper",
    },
  );
});

test("studio chat skill support only sends verified skills after lookup settles", () => {
  const skillOptions = buildStudioChatSkillOptions({
    userSkills: [
      {
        description: "更温柔一点",
        enabled: true,
        id: "skill.user.warm-helper",
        name: "温柔陪跑",
        updated_at: null,
      },
    ],
  });

  assert.deepEqual(
    resolveStudioSendableSkillSelection({
      conversationSkillId: "skill.user.missing-helper",
      nextTurnSkillId: "skill.user.warm-helper",
      skillLookupStatus: "loading",
      skillOptions,
    }),
    {
      conversationSkillId: null,
      nextTurnSkillId: null,
    },
  );
  assert.deepEqual(
    resolveStudioSendableSkillSelection({
      conversationSkillId: "skill.user.missing-helper",
      nextTurnSkillId: "skill.user.warm-helper",
      skillLookupStatus: "ready",
      skillOptions,
    }),
    {
      conversationSkillId: null,
      nextTurnSkillId: null,
    },
  );
  assert.deepEqual(
    resolveStudioSendableSkillSelection({
      conversationSkillId: "skill.user.missing-helper",
      nextTurnSkillId: "skill.user.warm-helper",
      skillLookupStatus: "error",
      skillOptions,
    }),
    {
      conversationSkillId: null,
      nextTurnSkillId: null,
    },
  );
  assert.equal(
    resolveStudioSkillSendBlockReason({
      conversationSkillId: "skill.user.missing-helper",
      nextTurnSkillId: "skill.user.warm-helper",
      skillLookupStatus: "loading",
      skillOptions,
    }),
    "当前 Skill 仍在确认中，确认完成后才能发送。",
  );
  assert.equal(
    resolveStudioSkillSendBlockReason({
      conversationSkillId: "skill.user.missing-helper",
      nextTurnSkillId: "skill.user.warm-helper",
      skillLookupStatus: "error",
      skillOptions,
    }),
    "当前已选 Skill 暂时不可用，请稍后重试，或先切回普通对话。",
  );
  assert.equal(
    resolveStudioSkillSendBlockReason({
      conversationSkillId: "skill.user.missing-helper",
      nextTurnSkillId: "skill.user.warm-helper",
      skillLookupStatus: "ready",
      skillOptions,
    }),
    "当前已选 Skill 已失效，请重新选择或切回普通对话。",
  );
  assert.equal(
    resolveStudioSkillSendBlockReason({
      conversationSkillId: null,
      nextTurnSkillId: null,
      skillLookupStatus: "loading",
      skillOptions,
    }),
    null,
  );
});

test("studio chat skill support shows pending state while selected skill is still loading", () => {
  const skillOptions = buildStudioChatSkillOptions({
    userSkills: [
      {
        description: "更温柔一点",
        enabled: true,
        id: "skill.user.warm-helper",
        name: "温柔陪跑",
        updated_at: null,
      },
    ],
  });

  assert.deepEqual(
    resolveStudioActiveSkillState({
      conversationSkillId: "skill.user.warm-helper",
      nextTurnSkillId: "skill.user.warm-helper",
      skillLookupStatus: "loading",
      skillsLoading: true,
      skillOptions,
    }),
    {
      conversationSkillId: "skill.user.warm-helper",
      conversationSkillLabel: null,
      detail: "Skill 列表仍在读取，确认完成后才会按当前 Skill 发送。",
      headline: "Skill 待确认",
      nextTurnSkillId: null,
      nextTurnSkillLabel: null,
    },
  );
});

test("studio chat skill support shows blocked state when selected skill cannot be verified", () => {
  const skillOptions = buildStudioChatSkillOptions({
    userSkills: [
      {
        description: "更温柔一点",
        enabled: true,
        id: "skill.user.warm-helper",
        name: "温柔陪跑",
        updated_at: null,
      },
    ],
  });

  assert.deepEqual(
    resolveStudioActiveSkillState({
      conversationSkillId: "skill.user.warm-helper",
      nextTurnSkillId: "skill.user.warm-helper",
      skillLookupStatus: "error",
      skillOptions,
    }),
    {
      conversationSkillId: "skill.user.warm-helper",
      conversationSkillLabel: null,
      detail: "当前已选 Skill 暂时无法确认，请稍后重试，或先切回普通对话。",
      headline: "Skill 暂不可用",
      nextTurnSkillId: null,
      nextTurnSkillLabel: null,
    },
  );
});

test("studio chat skill support shows invalid state when ready selection still contains missing skill ids", () => {
  const skillOptions = buildStudioChatSkillOptions({
    userSkills: [
      {
        description: "更温柔一点",
        enabled: true,
        id: "skill.user.warm-helper",
        name: "温柔陪跑",
        updated_at: null,
      },
    ],
  });

  assert.deepEqual(
    resolveStudioActiveSkillState({
      conversationSkillId: "skill.user.missing-helper",
      nextTurnSkillId: "skill.user.warm-helper",
      skillLookupStatus: "ready",
      skillOptions,
    }),
    {
      conversationSkillId: "skill.user.missing-helper",
      conversationSkillLabel: null,
      detail: "当前已选 Skill 已失效，请重新选择或切回普通对话。",
      headline: "Skill 已失效",
      nextTurnSkillId: "skill.user.warm-helper",
      nextTurnSkillLabel: null,
    },
  );
});

test("studio chat skill support filters by label, description, and scope", () => {
  const skillOptions = buildStudioChatSkillOptions({
    projectSkills: [
      {
        description: "项目统一口吻",
        enabled: true,
        id: "skill.project.outline",
        name: "大纲推进",
        updated_at: null,
      },
    ],
    userSkills: [
      {
        description: "更温柔地陪你往下写",
        enabled: true,
        id: "skill.user.warm",
        name: "温柔陪跑",
        updated_at: null,
      },
    ],
  });

  assert.deepEqual(
    filterStudioChatSkillOptions(skillOptions, "温柔").map((item) => item.value),
    ["skill.user.warm"],
  );
  assert.deepEqual(
    filterStudioChatSkillOptions(skillOptions, "统一口吻").map((item) => item.value),
    ["skill.project.outline"],
  );
  assert.deepEqual(
    filterStudioChatSkillOptions(skillOptions, "项目").map((item) => item.value),
    ["skill.project.outline"],
  );
  assert.deepEqual(
    filterStudioChatSkillOptions(skillOptions, "  "),
    skillOptions,
  );
});
