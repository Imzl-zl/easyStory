import assert from "node:assert/strict";
import test from "node:test";

import {
  buildAssistantReasoningShapeError,
  buildAssistantReasoningPayload,
  describeAssistantReasoningSelection,
  normalizeAssistantReasoningDraft,
  parseAssistantThinkingBudgetDraft,
  resolveAssistantReasoningModelName,
  resolveAssistantReasoningControl,
  resolveAssistantReasoningPreferredKind,
  sanitizeAssistantThinkingBudgetInput,
} from "./assistant-reasoning-support";

test("assistant reasoning support resolves protocol-aware controls", () => {
  assert.deepEqual(
    resolveAssistantReasoningControl({
      apiDialect: "openai_responses",
      modelName: "gpt-4.1",
    }),
    {
      description: "按当前 OpenAI 协议发送官方 `reasoning.effort` 参数；这里展示的是 OpenAI 协议族常见值集合，不代表当前模型的官方逐型号支持表。具体是否支持由模型或网关决定，不支持时会由上游显式返回错误。",
      kind: "openai",
      options: [
        { label: "跟随模型默认", value: "" },
        { label: "关闭思考", value: "none" },
        { label: "最少", value: "minimal" },
        { label: "低", value: "low" },
        { label: "中", value: "medium" },
        { label: "高", value: "high" },
        { label: "极高", value: "xhigh" },
      ],
      title: "思考强度",
    },
  );
  assert.deepEqual(
    resolveAssistantReasoningControl({
      apiDialect: "openai_chat_completions",
      modelName: "gpt-5.4",
    }),
    {
      description: "按当前 OpenAI 协议发送官方 `reasoning_effort` 参数；官方 OpenAI 端点会配合 `max_completion_tokens`，兼容网关可能仍使用 `max_tokens`。这里展示的是 OpenAI 协议族常见值集合，不代表当前模型的官方逐型号支持表。具体是否支持由模型或网关决定，不支持时会由上游显式返回错误。",
      kind: "openai",
      options: [
        { label: "跟随模型默认", value: "" },
        { label: "关闭思考", value: "none" },
        { label: "最少", value: "minimal" },
        { label: "低", value: "low" },
        { label: "中", value: "medium" },
        { label: "高", value: "high" },
        { label: "极高", value: "xhigh" },
      ],
      title: "思考强度",
    },
  );
  assert.deepEqual(
    resolveAssistantReasoningControl({
      apiDialect: "gemini_generate_content",
      modelName: "gemini-3.1-pro",
    }),
    {
      description: "按 Gemini 原生接口发送官方 thinkingLevel 参数；这里展示的是 Gemini 3 协议族常见值集合，不代表当前模型的官方逐型号支持表，例如部分 Pro 型号不支持 minimal。不支持时会由上游显式返回错误。",
      kind: "gemini_level",
      options: [
        { label: "跟随模型默认", value: "" },
        { label: "最少", value: "minimal" },
        { label: "低", value: "low" },
        { label: "中", value: "medium" },
        { label: "高", value: "high" },
      ],
      title: "思考等级",
    },
  );
  assert.deepEqual(
    resolveAssistantReasoningControl({
      apiDialect: "gemini_generate_content",
      modelName: "gemini-2.5-flash",
    }),
    {
      allowDisable: true,
      allowDynamic: true,
      description: "按 Gemini 原生接口发送官方 thinkingBudget 参数；这里仅校验基本格式，可留空跟随默认，也可填 0、-1 或正整数。0/-1/正整数范围是否有效按具体模型决定，例如 2.5 Pro 不能用 0，Flash Lite 的正整数预算最小是 512。不支持时会由上游显式返回错误。",
      kind: "gemini_budget",
      maxBudget: Number.MAX_SAFE_INTEGER,
      minBudget: 1,
      placeholder: "留空跟随默认，也可填 0、-1 或按模型范围填写正整数",
      title: "思考预算",
    },
  );
  assert.equal(
    resolveAssistantReasoningControl({
      apiDialect: "anthropic_messages",
      modelName: "gpt-5.4",
    }).kind,
    "none",
  );
  assert.deepEqual(
    resolveAssistantReasoningControl({
      modelName: "gpt-5.4",
    }),
    {
      description: "按最终 OpenAI 协议发送官方 reasoning 参数；若最终走 Responses 将使用 `reasoning.effort`，若最终走 Chat Completions 将使用 `reasoning_effort`。这里展示的是 OpenAI 协议族常见值集合，不代表当前模型的官方逐型号支持表。具体是否支持由模型或网关决定，不支持时会由上游显式返回错误。",
      kind: "openai",
      options: [
        { label: "跟随模型默认", value: "" },
        { label: "关闭思考", value: "none" },
        { label: "最少", value: "minimal" },
        { label: "低", value: "low" },
        { label: "中", value: "medium" },
        { label: "高", value: "high" },
        { label: "极高", value: "xhigh" },
      ],
      title: "思考强度",
    },
  );
  assert.equal(
    resolveAssistantReasoningModelName("", "gpt-5.4"),
    "gpt-5.4",
  );
});

test("assistant reasoning support sanitizes and parses thinking budgets", () => {
  assert.equal(sanitizeAssistantThinkingBudgetInput(" - 2a56 "), "-256");
  assert.equal(parseAssistantThinkingBudgetDraft("-1"), -1);
  assert.equal(parseAssistantThinkingBudgetDraft(""), null);
});

test("assistant reasoning support normalizes incompatible drafts and builds payloads", () => {
  const openaiControl = resolveAssistantReasoningControl({
    apiDialect: "openai_chat_completions",
    modelName: "gpt-5.4",
  });
  const geminiControl = resolveAssistantReasoningControl({
    apiDialect: "gemini_generate_content",
    modelName: "gemini-2.5-flash",
  });

  assert.deepEqual(
    normalizeAssistantReasoningDraft(
      {
        reasoningEffort: "high",
        thinkingBudget: "-1",
        thinkingLevel: "low",
      },
      openaiControl,
    ),
    {
      reasoningEffort: "high",
      thinkingBudget: "",
      thinkingLevel: "",
    },
  );
  assert.deepEqual(
    buildAssistantReasoningPayload(
      {
        reasoningEffort: "",
        thinkingBudget: "999999",
        thinkingLevel: "",
      },
      geminiControl,
    ),
    { thinking_budget: 999999 },
  );
  assert.equal(
    describeAssistantReasoningSelection(
      {
        reasoningEffort: "",
        thinkingBudget: "0",
        thinkingLevel: "",
      },
      geminiControl,
    ),
    "关闭思考",
  );
  assert.equal(
    buildAssistantReasoningShapeError({
      reasoningEffort: "high",
      thinkingBudget: "",
      thinkingLevel: "low",
    }),
    "reasoning_effort 不能和 thinking_level 或 thinking_budget 同时存在",
  );
  assert.equal(
    resolveAssistantReasoningPreferredKind({
      reasoningEffort: "",
      thinkingBudget: "0",
      thinkingLevel: "",
    }),
    "gemini_budget",
  );
  assert.deepEqual(
    buildAssistantReasoningPayload(
      {
        reasoningEffort: "high",
        thinkingBudget: "",
        thinkingLevel: "low",
      },
      openaiControl,
      { preserveInvalidShape: true },
    ),
    {
      reasoning_effort: "high",
      thinking_level: "low",
    },
  );
});
