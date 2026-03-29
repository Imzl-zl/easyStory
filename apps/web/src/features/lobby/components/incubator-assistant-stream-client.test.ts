import assert from "node:assert/strict";
import test from "node:test";

import { runAssistantTurnStream } from "@/lib/api/assistant";

test("assistant stream client returns buffered content when stream ends without completed event", async () => {
  const originalFetch = global.fetch;
  const streamBody = "event: chunk\ndata: {\"delta\":\"好的，这是回复。\"}\n\n";

  global.fetch = async () =>
    new Response(
      new ReadableStream({
        start(controller) {
          controller.enqueue(new TextEncoder().encode(streamBody));
          controller.close();
        },
      }),
      {
        headers: {
          "Content-Type": "text/event-stream",
        },
        status: 200,
      },
    );

  const chunks: string[] = [];

  try {
    const result = await runAssistantTurnStream(
      {
        messages: [{ content: "测试", role: "user" }],
        model: {
          max_tokens: 8192,
          name: "gemini-2.5-flash",
          provider: "薄荷",
        },
        skill_id: "skill.assistant.general_chat",
      },
      {
        onChunk: (delta) => chunks.push(delta),
      },
    );

    assert.deepEqual(chunks, ["好的，这是回复。"]);
    assert.equal(result.content, "好的，这是回复。");
    assert.equal(result.provider, "薄荷");
    assert.equal(result.model_name, "gemini-2.5-flash");
  } finally {
    global.fetch = originalFetch;
  }
});
