import assert from "node:assert/strict";
import test from "node:test";

import {
  buildStudioChatSkillOptions,
  filterStudioChatSkillOptions,
  normalizeStudioSkillId,
  resolveStudioActiveSkillState,
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
      conversationSkillLabel: "已失效 Skill：skill.user.missing-helper",
      detail: "后续消息都会沿用这个 Skill",
      headline: "当前会话 · 已失效 Skill：skill.user.missing-helper",
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
      conversationSkillLabel: "正在读取 Skill…",
      detail: "后续消息都会沿用这个 Skill",
      headline: "当前会话 · 正在读取 Skill…",
      nextTurnSkillId: null,
      nextTurnSkillLabel: null,
    },
  );
});

test("studio chat skill support normalizes blank skill ids to null", () => {
  assert.equal(normalizeStudioSkillId(undefined), null);
  assert.equal(normalizeStudioSkillId("  "), null);
  assert.equal(normalizeStudioSkillId(" skill.user.helper "), "skill.user.helper");
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
