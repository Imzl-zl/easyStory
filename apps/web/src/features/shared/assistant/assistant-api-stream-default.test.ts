import assert from "node:assert/strict";
import test from "node:test";

import {
  AssistantTurnStreamTerminalError,
  runAssistantTurn,
  runAssistantTurnStream,
} from "@/lib/api/assistant";

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
      conversation_id: "conversation-api-test",
      client_turn_id: "turn-api-test-1",
      messages: [{ content: "测试", role: "user" }],
      requested_write_scope: "disabled",
      skill_id: "skill.assistant.general_chat",
    });
  } finally {
    global.fetch = originalFetch;
  }

  assert.ok(requestBody);
  assert.equal(JSON.parse(requestBody).stream, false);
});

test("assistant api stream ignores tool events and resolves final output", async () => {
  const originalFetch = global.fetch;

  global.fetch = async () => new Response(
    [
      "event: run_started",
      'data: {"run_id":"run-1","conversation_id":"conversation-1","client_turn_id":"turn-1","event_seq":1,"state_version":1,"ts":"2026-04-05T00:00:00Z","requested_write_scope":"disabled","requested_write_targets":[]}',
      "",
      "event: tool_call_start",
      'data: {"run_id":"run-1","conversation_id":"conversation-1","client_turn_id":"turn-1","event_seq":2,"state_version":2,"ts":"2026-04-05T00:00:01Z","tool_call_id":"call-1","tool_name":"project.read_documents"}',
      "",
      "event: tool_call_result",
      'data: {"run_id":"run-1","conversation_id":"conversation-1","client_turn_id":"turn-1","event_seq":3,"state_version":3,"ts":"2026-04-05T00:00:02Z","tool_call_id":"call-1","tool_name":"project.read_documents","status":"completed"}',
      "",
      "event: completed",
      'data: {"run_id":"run-1","conversation_id":"conversation-1","client_turn_id":"turn-1","event_seq":4,"state_version":4,"ts":"2026-04-05T00:00:03Z","content":"好的","hook_results":[],"mcp_servers":[],"model_name":"gpt-5.4","provider":"openai","skill_id":null,"agent_id":null,"output_items":[],"output_meta":{},"input_tokens":1,"output_tokens":1,"total_tokens":2}',
      "",
    ].join("\n"),
    {
      headers: {
        "Content-Type": "text/event-stream",
      },
      status: 200,
    },
  );

  try {
    const result = await runAssistantTurnStream({
      conversation_id: "conversation-1",
      client_turn_id: "turn-1",
      messages: [{ content: "测试", role: "user" }],
      requested_write_scope: "disabled",
    }, {
      onChunk: () => {},
    });
    assert.equal(result.content, "好的");
    assert.equal(result.run_id, "run-1");
  } finally {
    global.fetch = originalFetch;
  }
});

test("assistant api stream surfaces structured error payload message", async () => {
  const originalFetch = global.fetch;

  global.fetch = async () => new Response(
    [
      "event: error",
      'data: {"run_id":"run-1","conversation_id":"conversation-1","client_turn_id":"turn-1","event_seq":2,"state_version":2,"ts":"2026-04-05T00:00:01Z","message":"本轮工具调用次数已达上限，已停止继续执行。","code":"tool_loop_exhausted","terminal_status":"failed","write_effective":false}',
      "",
    ].join("\n"),
    {
      headers: {
        "Content-Type": "text/event-stream",
      },
      status: 200,
    },
  );

  try {
    await assert.rejects(async () => runAssistantTurnStream({
      conversation_id: "conversation-1",
      client_turn_id: "turn-1",
      messages: [{ content: "测试", role: "user" }],
      requested_write_scope: "disabled",
    }, {
      onChunk: () => {},
    }), (error: unknown) => {
      assert(error instanceof AssistantTurnStreamTerminalError);
      assert.equal(error.message, "本轮工具调用次数已达上限，已停止继续执行。");
      assert.equal(error.code, "tool_loop_exhausted");
      assert.equal(error.terminalStatus, "failed");
      assert.equal(error.writeEffective, false);
      assert.equal(error.runId, "run-1");
      assert.equal(error.conversationId, "conversation-1");
      assert.equal(error.clientTurnId, "turn-1");
      assert.equal(error.eventSeq, 2);
      assert.equal(error.stateVersion, 2);
      assert.equal(error.ts, "2026-04-05T00:00:01Z");
      return true;
    });
  } finally {
    global.fetch = originalFetch;
  }
});

test("assistant api stream falls back to default cancellation message when cancelled tool result omits summary", async () => {
  const originalFetch = global.fetch;

  global.fetch = async () => new Response(
    [
      "event: run_started",
      'data: {"run_id":"run-1","conversation_id":"conversation-1","client_turn_id":"turn-1","event_seq":1,"state_version":1,"ts":"2026-04-05T00:00:00Z","requested_write_scope":"disabled","requested_write_targets":[]}',
      "",
      "event: tool_call_result",
      'data: {"run_id":"run-1","conversation_id":"conversation-1","client_turn_id":"turn-1","event_seq":2,"state_version":2,"ts":"2026-04-05T00:00:01Z","tool_call_id":"call-1","tool_name":"project.read_documents","status":"cancelled"}',
      "",
    ].join("\n"),
    {
      headers: {
        "Content-Type": "text/event-stream",
      },
      status: 200,
    },
  );

  try {
    await assert.rejects(async () => runAssistantTurnStream({
      conversation_id: "conversation-1",
      client_turn_id: "turn-cancelled-1",
      messages: [{ content: "测试", role: "user" }],
      requested_write_scope: "disabled",
    }, {
      onChunk: () => {},
    }), (error: unknown) => {
      assert(error instanceof AssistantTurnStreamTerminalError);
      assert.equal(error.message, "本轮已停止，当前工具未执行。");
      assert.equal(error.code, "cancel_requested");
      assert.equal(error.terminalStatus, "cancelled");
      assert.equal(error.runId, "run-1");
      assert.equal(error.conversationId, "conversation-1");
      assert.equal(error.clientTurnId, "turn-1");
      assert.equal(error.eventSeq, 2);
      assert.equal(error.stateVersion, 2);
      assert.equal(error.ts, "2026-04-05T00:00:01Z");
      return true;
    });
  } finally {
    global.fetch = originalFetch;
  }
});

test("assistant api stream prefers structured error over prior cancelled tool result", async () => {
  const originalFetch = global.fetch;

  global.fetch = async () => new Response(
    [
      "event: run_started",
      'data: {"run_id":"run-1","conversation_id":"conversation-1","client_turn_id":"turn-1","event_seq":1,"state_version":1,"ts":"2026-04-05T00:00:00Z","requested_write_scope":"disabled","requested_write_targets":[]}',
      "",
      "event: tool_call_result",
      'data: {"run_id":"run-1","conversation_id":"conversation-1","client_turn_id":"turn-1","event_seq":2,"state_version":2,"ts":"2026-04-05T00:00:01Z","tool_call_id":"call-1","tool_name":"project.read_documents","status":"cancelled","result_summary":{"message":"本轮已停止，当前工具未执行。"}}',
      "",
      "event: error",
      'data: {"run_id":"run-1","conversation_id":"conversation-1","client_turn_id":"turn-1","event_seq":3,"state_version":3,"ts":"2026-04-05T00:00:02Z","message":"本轮工具调用次数已达上限，已停止继续执行。","code":"tool_loop_exhausted","terminal_status":"failed","write_effective":false}',
      "",
    ].join("\n"),
    {
      headers: {
        "Content-Type": "text/event-stream",
      },
      status: 200,
    },
  );

  try {
    await assert.rejects(async () => runAssistantTurnStream({
      conversation_id: "conversation-1",
      client_turn_id: "turn-error-priority-1",
      messages: [{ content: "测试", role: "user" }],
      requested_write_scope: "disabled",
    }, {
      onChunk: () => {},
    }), (error: unknown) => {
      assert(error instanceof AssistantTurnStreamTerminalError);
      assert.equal(error.message, "本轮工具调用次数已达上限，已停止继续执行。");
      assert.equal(error.code, "tool_loop_exhausted");
      assert.equal(error.terminalStatus, "failed");
      assert.equal(error.writeEffective, false);
      assert.equal(error.runId, "run-1");
      assert.equal(error.conversationId, "conversation-1");
      assert.equal(error.clientTurnId, "turn-1");
      assert.equal(error.eventSeq, 3);
      assert.equal(error.stateVersion, 3);
      assert.equal(error.ts, "2026-04-05T00:00:02Z");
      return true;
    });
  } finally {
    global.fetch = originalFetch;
  }
});

test("assistant api stream converts abort into cancelled terminal error", async () => {
  const originalFetch = global.fetch;

  global.fetch = async () => {
    throw new DOMException("The operation was aborted.", "AbortError");
  };

  try {
    await assert.rejects(async () => runAssistantTurnStream({
      conversation_id: "conversation-1",
      client_turn_id: "turn-abort-1",
      messages: [{ content: "测试", role: "user" }],
      requested_write_scope: "disabled",
    }, {
      onChunk: () => {},
    }), (error: unknown) => {
      assert(error instanceof AssistantTurnStreamTerminalError);
      assert.equal(error.message, "本轮已停止。");
      assert.equal(error.code, "cancel_requested");
      assert.equal(error.terminalStatus, "cancelled");
      assert.equal(error.writeEffective, false);
      return true;
    });
  } finally {
    global.fetch = originalFetch;
  }
});

test("assistant api stream surfaces interrupted stream as structured terminal error with last run meta", async () => {
  const originalFetch = global.fetch;

  global.fetch = async () => new Response(
    [
      "event: run_started",
      'data: {"run_id":"run-interrupted-1","conversation_id":"conversation-interrupted-1","client_turn_id":"turn-interrupted-1","event_seq":1,"state_version":1,"ts":"2026-04-06T00:00:00Z","requested_write_scope":"disabled","requested_write_targets":[]}',
      "",
    ].join("\n"),
    {
      headers: {
        "Content-Type": "text/event-stream",
      },
      status: 200,
    },
  );

  try {
    await assert.rejects(async () => runAssistantTurnStream({
      conversation_id: "conversation-interrupted-1",
      client_turn_id: "turn-interrupted-1",
      messages: [{ content: "测试", role: "user" }],
      requested_write_scope: "disabled",
    }, {
      onChunk: () => {},
    }), (error: unknown) => {
      assert(error instanceof AssistantTurnStreamTerminalError);
      assert.equal(error.message, "实时回复意外中断，请重试。");
      assert.equal(error.code, "stream_interrupted");
      assert.equal(error.terminalStatus, "failed");
      assert.equal(error.runId, "run-interrupted-1");
      assert.equal(error.conversationId, "conversation-interrupted-1");
      assert.equal(error.clientTurnId, "turn-interrupted-1");
      assert.equal(error.eventSeq, 1);
      assert.equal(error.stateVersion, 1);
      assert.equal(error.ts, "2026-04-06T00:00:00Z");
      return true;
    });
  } finally {
    global.fetch = originalFetch;
  }
});

test("assistant api stream surfaces malformed payload as structured terminal error with last run meta", async () => {
  const originalFetch = global.fetch;

  global.fetch = async () => new Response(
    [
      "event: run_started",
      'data: {"run_id":"run-invalid-1","conversation_id":"conversation-invalid-1","client_turn_id":"turn-invalid-1","event_seq":1,"state_version":1,"ts":"2026-04-06T00:00:00Z","requested_write_scope":"disabled","requested_write_targets":[]}',
      "",
      "event: chunk",
      'data: {"run_id":"run-invalid-1","conversation_id":"conversation-invalid-1","client_turn_id":"turn-invalid-1","event_seq":2,"state_version":2,"ts":"2026-04-06T00:00:01Z","delta":"半截"',
      "",
    ].join("\n"),
    {
      headers: {
        "Content-Type": "text/event-stream",
      },
      status: 200,
    },
  );

  try {
    await assert.rejects(async () => runAssistantTurnStream({
      conversation_id: "conversation-invalid-1",
      client_turn_id: "turn-invalid-1",
      messages: [{ content: "测试", role: "user" }],
      requested_write_scope: "disabled",
    }, {
      onChunk: () => {},
    }), (error: unknown) => {
      assert(error instanceof AssistantTurnStreamTerminalError);
      assert.equal(error.message, "实时回复数据异常，请重试。");
      assert.equal(error.code, "stream_payload_invalid");
      assert.equal(error.terminalStatus, "failed");
      assert.equal(error.runId, "run-invalid-1");
      assert.equal(error.conversationId, "conversation-invalid-1");
      assert.equal(error.clientTurnId, "turn-invalid-1");
      assert.equal(error.eventSeq, 1);
      assert.equal(error.stateVersion, 1);
      assert.equal(error.ts, "2026-04-06T00:00:00Z");
      return true;
    });
  } finally {
    global.fetch = originalFetch;
  }
});
