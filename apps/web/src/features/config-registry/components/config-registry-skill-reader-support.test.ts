import assert from "node:assert/strict";
import test from "node:test";

import type { SkillConfigDetail } from "@/lib/api/types";

import {
  buildSkillMarkdown,
  buildSkillModelDocument,
  buildSkillModelRows,
  buildSkillResourceItems,
  buildSkillSchemaDocument,
  buildSkillSchemaSections,
  extractSkillPromptRefs,
  resolveSkillSchemaMode,
  resolveSkillSchemaModeLabel,
} from "./config-registry-skill-reader-support";

test("extractSkillPromptRefs keeps prompt variables unique", () => {
  assert.deepEqual(
    extractSkillPromptRefs("你好 {{ user_input }} {{ user_input }} {{ conversation_history }}"),
    ["user_input", "conversation_history"],
  );
});

test("resolveSkillSchemaMode prefers variables over io mode", () => {
  const detail = createSkillDetail();
  assert.equal(resolveSkillSchemaMode(detail), "variables");
  assert.equal(resolveSkillSchemaModeLabel(detail), "变量注入");
});

test("buildSkillSchemaSections reports io empty messages when using variables mode", () => {
  const [variablesSection, inputsSection, outputsSection] = buildSkillSchemaSections(createSkillDetail());
  assert.equal(variablesSection.title, "可用变量");
  assert.equal(variablesSection.items[0]?.key, "user_input");
  assert.equal(inputsSection.emptyMessage, "当前 Skill 使用变量注入，不单列输入结构。");
  assert.equal(outputsSection.emptyMessage, "当前 Skill 使用变量注入，不单列输出结构。");
});

test("buildSkillModelRows formats configured model fields", () => {
  assert.deepEqual(buildSkillModelRows(createSkillDetail().model), [
    { label: "服务来源", value: "openai" },
    { label: "模型名称", value: "gpt-4.1" },
    { label: "单次回复上限", value: "4000" },
    { label: "发散程度", value: "0.6" },
    { label: "附加能力", value: "streaming、tool_calling" },
  ]);
});

test("buildSkillResourceItems follows file-like skill structure", () => {
  assert.deepEqual(
    buildSkillResourceItems(createSkillDetail()).map((item) => item.filename),
    ["SKILL.md", "schema.generated.json", "model.generated.yaml", "runtime.generated.json"],
  );
});

test("buildSkillMarkdown renders frontmatter and prompt block", () => {
  const document = buildSkillMarkdown(createSkillDetail());
  assert.match(document, /^---/);
  assert.match(document, /name: 通用对话助手/);
  assert.match(document, /## Prompt/);
  assert.match(document, /```text/);
  assert.match(document, /你好 {{ user_input }}/);
});

test("buildSkillSchemaDocument includes mode and variables", () => {
  const document = buildSkillSchemaDocument(createSkillDetail());
  assert.match(document, /"mode": "variables"/);
  assert.match(document, /"user_input"/);
});

test("buildSkillModelDocument outputs yaml-like config", () => {
  const document = buildSkillModelDocument(createSkillDetail().model);
  assert.match(document, /provider: openai/);
  assert.match(document, /model: gpt-4.1/);
  assert.match(document, /required_capabilities: streaming、tool_calling/);
});

function createSkillDetail(): SkillConfigDetail {
  return {
    author: null,
    category: "assistant",
    description: "用于通用对话",
    id: "skill.assistant.general_chat",
    inputs: {},
    model: {
      max_tokens: 4000,
      name: "gpt-4.1",
      provider: "openai",
      required_capabilities: ["streaming", "tool_calling"],
      temperature: 0.6,
    },
    name: "通用对话助手",
    outputs: {},
    prompt: "你好 {{ user_input }}",
    tags: [],
    variables: {
      user_input: {
        default: null,
        description: "当前输入",
        required: true,
        type: "string",
      },
    },
    version: "1.0.0",
  };
}
