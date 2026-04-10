import assert from "node:assert/strict";
import test from "node:test";

import {
  buildAssistantModelOverride,
  resolveChatOutputModeLabel,
  resolveIncubatorAssistantReply,
} from "@/features/shared/assistant/assistant-chat-support";
import {
  appendIncubatorMessageDelta,
  buildIncubatorConversationFingerprint,
  buildIncubatorConversationText,
  buildSuggestedProjectName,
  createIncubatorInitialMessages,
  createIncubatorMessage,
  INCUBATOR_DEFAULT_PROVIDER,
  INCUBATOR_INTERRUPTED_REPLY_MESSAGE,
  INCUBATOR_NO_SKILL_LABEL,
  INCUBATOR_PENDING_REPLY_MESSAGE,
  resolveFailedIncubatorReply,
  resolveIncubatorAgentId,
  resolveIncubatorAgentLabel,
  resolveIncubatorHookIds,
  resolveInterruptedIncubatorReply,
  resolveIncubatorSkillLabel,
  resolveIncubatorSkillId,
  shouldShowPromptSuggestions,
  shouldSubmitIncubatorComposer,
  toggleIncubatorHookId,
} from "@/features/lobby/components/incubator/incubator-chat-support";

test("incubator chat support builds draft transcript from first user message onward", () => {
  const messages = [
    ...createIncubatorInitialMessages(),
    createIncubatorMessage("user", "我想写一个修仙故事"),
    createIncubatorMessage("assistant", "可以先做成宗门成长线。"),
    createIncubatorMessage("user", "主角想替家族翻案"),
  ];

  assert.equal(
    buildIncubatorConversationText(messages),
    [
      "用户：我想写一个修仙故事",
      "助手：可以先做成宗门成长线。",
      "用户：主角想替家族翻案",
    ].join("\n\n"),
  );
});

test("incubator chat support starts from visible assistant welcome without hidden system prompt", () => {
  const messages = createIncubatorInitialMessages();
  assert.equal(messages.length, 1);
  assert.equal(messages[0]?.role, "assistant");
  assert.equal(messages[0]?.hidden, undefined);
});

test("incubator chat support builds stable fingerprints and model overrides", () => {
  const messages = [
    ...createIncubatorInitialMessages(),
    createIncubatorMessage("user", "给我三个方向"),
  ];

  assert.deepEqual(
    JSON.parse(buildIncubatorConversationFingerprint(messages, {
      agentId: "",
      hookIds: [],
      modelName: "",
      provider: INCUBATOR_DEFAULT_PROVIDER,
      reasoningEffort: "",
      skillId: "",
      thinkingBudget: "",
      thinkingLevel: "",
    })),
    {
      agentId: "",
      conversationText: "用户：给我三个方向",
      hookIds: [],
      modelName: "",
      provider: INCUBATOR_DEFAULT_PROVIDER,
      reasoningEffort: "",
      skillId: "",
      thinkingBudget: "",
      thinkingLevel: "",
    },
  );
  assert.equal(
    buildAssistantModelOverride({
      maxOutputTokens: "4096",
      modelName: "",
      provider: INCUBATOR_DEFAULT_PROVIDER,
      reasoningEffort: "",
      thinkingBudget: "",
      thinkingLevel: "",
    }),
    undefined,
  );
  assert.deepEqual(
    buildAssistantModelOverride({
      maxOutputTokens: "",
      modelName: "",
      provider: "openai",
      reasoningEffort: "",
      thinkingBudget: "",
      thinkingLevel: "",
    }),
    { name: undefined, provider: "openai" },
  );
  assert.deepEqual(
    buildAssistantModelOverride({
      maxOutputTokens: "8192",
      modelName: "gpt-5.4",
      provider: "openai",
      reasoningEffort: "high",
      thinkingBudget: "",
      thinkingLevel: "",
    }, {
      apiDialect: "openai_responses",
    }),
    { max_tokens: 8192, name: "gpt-5.4", provider: "openai", reasoning_effort: "high" },
  );
  assert.deepEqual(
    buildAssistantModelOverride({
      maxOutputTokens: "",
      modelName: "",
      provider: "openai",
      reasoningEffort: "high",
      thinkingBudget: "",
      thinkingLevel: "",
    }, {
      apiDialect: "openai_responses",
      defaultModelName: "gpt-5.4",
    }),
    { name: undefined, provider: "openai", reasoning_effort: "high" },
  );
  assert.equal(resolveChatOutputModeLabel(true), "边写边显示");
  assert.equal(resolveChatOutputModeLabel(false), "生成后整体显示");
  assert.equal(resolveIncubatorSkillId(undefined), "");
  assert.equal(resolveIncubatorAgentId(undefined), "");
  assert.deepEqual(resolveIncubatorHookIds(["hook.b", " hook.a ", "hook.b"]), ["hook.a", "hook.b"]);
  assert.deepEqual(toggleIncubatorHookId(["hook.a"], "hook.b"), ["hook.a", "hook.b"]);
  assert.deepEqual(toggleIncubatorHookId(["hook.a", "hook.b"], "hook.a"), ["hook.b"]);
  assert.equal(
    resolveIncubatorSkillLabel(
      [{ label: INCUBATOR_NO_SKILL_LABEL, value: "" }],
      "skill.user.story-helper-a1b2c3",
    ),
    "当前 Skill 不可用：skill.user.story-helper-a1b2c3",
  );
  assert.equal(
    resolveIncubatorAgentLabel(
      [{ label: "温柔陪跑", value: "agent.user.story-coach-a1b2c3" }],
      "agent.user.missing-a1b2c3",
    ),
    "当前 Agent 不可用：agent.user.missing-a1b2c3",
  );
});

test("incubator chat support suggests project names from available setting signals", () => {
  assert.equal(
    buildSuggestedProjectName({
      genre: "玄幻",
      protagonist: { name: "林昭" },
    }),
    "林昭的玄幻故事",
  );
  assert.equal(
    buildSuggestedProjectName({
      protagonist: { identity: "宗门弃徒" },
    }),
    "宗门弃徒成长记",
  );
  assert.equal(buildSuggestedProjectName({}), "未命名新故事");
});

test("incubator chat support only shows suggestions before the first user message", () => {
  assert.equal(shouldShowPromptSuggestions(false), true);
  assert.equal(shouldShowPromptSuggestions(true), false);
});

test("incubator chat support uses Enter to submit and keeps Shift+Enter for newline", () => {
  assert.equal(
    shouldSubmitIncubatorComposer({ isComposing: false, key: "Enter", shiftKey: false }),
    true,
  );
  assert.equal(
    shouldSubmitIncubatorComposer({ isComposing: false, key: "Enter", shiftKey: true }),
    false,
  );
  assert.equal(
    shouldSubmitIncubatorComposer({ isComposing: true, key: "Enter", shiftKey: false }),
    false,
  );
  assert.equal(
    shouldSubmitIncubatorComposer({ isComposing: false, key: "a", shiftKey: false }),
    false,
  );
});

test("incubator chat support turns retired model replies into error guidance", () => {
  assert.deepEqual(
    resolveIncubatorAssistantReply(
      "Gemini 3 Pro is no longer available. Please switch to Gemini 3.1 Pro in the latest version of Antigravity.",
    ),
    {
      content: "当前默认模型已不可用，请换成可用模型后再试。上游提示：Gemini 3 Pro is no longer available. Please switch to Gemini 3.1 Pro in the latest version of Antigravity. 你可以先到“模型连接”里修改默认模型，再回来继续聊天。",
      status: "error",
    },
  );
});

test("incubator chat support replaces pending placeholder with streamed chunks", () => {
  const pendingMessage = createIncubatorMessage("assistant", INCUBATOR_PENDING_REPLY_MESSAGE, {
    status: "pending",
  });
  const firstChunk = appendIncubatorMessageDelta([pendingMessage], pendingMessage.id, "先给你三个方向");
  const secondChunk = appendIncubatorMessageDelta(firstChunk, pendingMessage.id, "，每个都能直接展开。");

  assert.equal(firstChunk[0]?.content, "先给你三个方向");
  assert.equal(secondChunk[0]?.content, "先给你三个方向，每个都能直接展开。");
});

test("incubator chat support keeps partial reply when streaming is interrupted", () => {
  assert.equal(resolveInterruptedIncubatorReply(INCUBATOR_PENDING_REPLY_MESSAGE), null);
  assert.equal(
    resolveInterruptedIncubatorReply("先给你两个方向"),
    `先给你两个方向\n\n${INCUBATOR_INTERRUPTED_REPLY_MESSAGE}`,
  );
});

test("incubator chat support preserves truncation reason when partial content already exists", () => {
  assert.equal(
    resolveFailedIncubatorReply(
      "4. **情感与宿命感更强：**\n不",
      "上游在输出尚未完成时提前停止了这次回复，当前只收到部分内容（stop_reason=length）。请在“模型与连接”里调高单次回复上限，或切换更稳定的连接后重试。",
    ),
    "4. **情感与宿命感更强：**\n不\n\n上游在输出尚未完成时提前停止了这次回复，当前只收到部分内容（stop_reason=length）。请在“模型与连接”里调高单次回复上限，或切换更稳定的连接后重试。",
  );
});
