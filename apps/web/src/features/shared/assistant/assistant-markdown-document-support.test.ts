import assert from "node:assert/strict";
import test from "node:test";

import {
  extractAssistantMarkdownDocument,
  matchAssistantMarkdownDocument,
} from "./assistant-markdown-document-support";

test("extractAssistantMarkdownDocument returns inner markdown for fenced markdown blocks", () => {
  assert.equal(
    extractAssistantMarkdownDocument("```markdown\n# 标题\n\n## 小节\n内容\n```"),
    "# 标题\n\n## 小节\n内容",
  );
});

test("matchAssistantMarkdownDocument keeps preface text around fenced markdown blocks", () => {
  assert.deepEqual(
    matchAssistantMarkdownDocument("好的，这是整理后的文档：\n\n```markdown\n# 标题\n\n## 小节\n内容\n```\n\n你可以继续补细节。"),
    {
      body: "# 标题\n\n## 小节\n内容",
      leadingText: "好的，这是整理后的文档：",
      trailingText: "你可以继续补细节。",
    },
  );
});

test("extractAssistantMarkdownDocument detects standalone markdown documents", () => {
  assert.equal(
    extractAssistantMarkdownDocument("# 世界观设定\n\n## 故事背景\n内容\n\n## 主要人物\n内容"),
    "# 世界观设定\n\n## 故事背景\n内容\n\n## 主要人物\n内容",
  );
});

test("extractAssistantMarkdownDocument ignores regular chat answers", () => {
  assert.equal(extractAssistantMarkdownDocument("我建议先补一下主角动机，再继续往下写。"), null);
});

test("extractAssistantMarkdownDocument ignores structured answers without a primary title", () => {
  assert.equal(
    extractAssistantMarkdownDocument("## 问题分析\n这里先看冲突。\n\n## 修改建议\n这里再给出方案。"),
    null,
  );
});
