import assert from "node:assert/strict";
import test from "node:test";

import { parseAssistantMarkdownDocument } from "@/features/settings/components/assistant/common/assistant-markdown-document-support";

test("assistant markdown support parses literal block scalars in frontmatter", () => {
  const parsed = parseAssistantMarkdownDocument(`---
name: novel-writer
description: |
  第一行说明
  第二行说明

  第三段说明
model:
  provider: "openai"
  max_tokens: 4096
---

正文`);

  assert.deepEqual(parsed.frontmatter, {
    description: "第一行说明\n第二行说明\n\n第三段说明",
    model: {
      max_tokens: 4096,
      provider: "openai",
    },
    name: "novel-writer",
  });
  assert.equal(parsed.body, "正文");
});

test("assistant markdown support parses folded block scalars in frontmatter", () => {
  const parsed = parseAssistantMarkdownDocument(`---
name: folded-skill
description: >
  第一行说明
  第二行说明

  第三段说明
---

正文`);

  assert.equal(parsed.frontmatter.description, "第一行说明 第二行说明\n\n第三段说明");
});
