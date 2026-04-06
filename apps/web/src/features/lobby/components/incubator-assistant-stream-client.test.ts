import assert from "node:assert/strict";
import test from "node:test";

import { runAssistantTurnStream } from "@/lib/api/assistant";

test("assistant stream client rejects partial content when stream ends without completed event", async () => {
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
    await assert.rejects(
      runAssistantTurnStream(
        {
          conversation_id: "conversation-stream-test",
          client_turn_id: "turn-stream-test-1",
          messages: [{ content: "测试", role: "user" }],
          model: {
            max_tokens: 8192,
            name: "gemini-2.5-flash",
            provider: "薄荷",
          },
          requested_write_scope: "disabled",
          skill_id: "skill.assistant.general_chat",
        },
        {
          onChunk: (delta) => chunks.push(delta),
        },
      ),
      /实时回复意外中断，请重试/,
    );
    assert.deepEqual(chunks, ["好的，这是回复。"]);
  } finally {
    global.fetch = originalFetch;
  }
});

test("assistant stream client surfaces cancelled tool result when stream closes after cancellation", async () => {
  const originalFetch = global.fetch;
  const streamBody = [
    "event: run_started",
    'data: {"run_id":"run-1","conversation_id":"conversation-1","client_turn_id":"turn-1","event_seq":1,"state_version":1,"ts":"2026-04-05T00:00:00Z","requested_write_scope":"disabled","requested_write_targets":[]}',
    "",
    "event: tool_call_start",
    'data: {"run_id":"run-1","conversation_id":"conversation-1","client_turn_id":"turn-1","event_seq":2,"state_version":2,"ts":"2026-04-05T00:00:01Z","tool_call_id":"call-1","tool_name":"project.read_documents"}',
    "",
    "event: tool_call_result",
    'data: {"run_id":"run-1","conversation_id":"conversation-1","client_turn_id":"turn-1","event_seq":3,"state_version":3,"ts":"2026-04-05T00:00:02Z","tool_call_id":"call-1","tool_name":"project.read_documents","status":"cancelled","result_summary":{"message":"本轮已停止，当前工具未执行。"}}',
    "",
  ].join("\n");

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

  try {
    await assert.rejects(
      runAssistantTurnStream(
        {
          conversation_id: "conversation-stream-test",
          client_turn_id: "turn-stream-test-cancelled",
          messages: [{ content: "测试", role: "user" }],
          requested_write_scope: "disabled",
        },
        {
          onChunk: () => {},
        },
      ),
      /本轮已停止，当前工具未执行/,
    );
  } finally {
    global.fetch = originalFetch;
  }
});
