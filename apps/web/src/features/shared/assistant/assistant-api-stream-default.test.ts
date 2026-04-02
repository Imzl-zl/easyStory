import assert from "node:assert/strict";
import test from "node:test";

import { runAssistantTurn } from "@/lib/api/assistant";

test("assistant api sends explicit buffered flag for non-stream turn requests", async () => {
  const originalFetch = global.fetch;
  let requestBody: string | undefined;

  global.fetch = async (_input, init) => {
    requestBody = init?.body as string | undefined;
    return new Response(
      JSON.stringify({
        content: "好的",
        hook_results: [],
        mcp_servers: [],
        model_name: "gpt-5.4",
        provider: "openai",
        skill_id: "skill.assistant.general_chat",
      }),
      {
        headers: {
          "Content-Type": "application/json",
        },
        status: 200,
      },
    );
  };

  try {
    await runAssistantTurn({
      messages: [{ content: "测试", role: "user" }],
      skill_id: "skill.assistant.general_chat",
    });
  } finally {
    global.fetch = originalFetch;
  }

  assert.ok(requestBody);
  assert.equal(JSON.parse(requestBody).stream, false);
});
