import assert from "node:assert/strict";
import test from "node:test";

import {
  collectStudioWriteEffectsFromTurnResult,
  isStudioAssistantWriteSuccessStatus,
  resolveStudioWriteEffectFromToolCallResult,
  resolveStudioWriteEffectFromToolCallStart,
} from "@/features/studio/components/chat/studio-chat-write-effects";

test("resolveStudioWriteEffectFromToolCallStart keeps target path for write tool", () => {
  assert.deepEqual(
    resolveStudioWriteEffectFromToolCallStart({
      target_summary: {
        base_version: "sha256:cast-v1",
        path: "设定/人物.md",
      },
      tool_call_id: "call-write-1",
      tool_name: "project.write_document",
    }),
    {
      paths: ["设定/人物.md"],
      status: "started",
      toolCallId: "call-write-1",
    },
  );
});

test("resolveStudioWriteEffectFromToolCallStart treats edit tool as write effect", () => {
  assert.deepEqual(
    resolveStudioWriteEffectFromToolCallStart({
      target_summary: {
        edit_count: 1,
        path: "设定/人物.md",
      },
      tool_call_id: "call-edit-1",
      tool_name: "project.edit_document",
    }),
    {
      paths: ["设定/人物.md"],
      status: "started",
      toolCallId: "call-edit-1",
    },
  );
});

test("resolveStudioWriteEffectFromToolCallResult falls back to start paths when error summary has no path", () => {
  assert.deepEqual(
    resolveStudioWriteEffectFromToolCallResult(
      {
        result_summary: {
          error_code: "version_conflict",
          message: "目标文稿版本已变化。",
        },
        status: "errored",
        tool_call_id: "call-write-1",
        tool_name: "project.write_document",
      },
      ["设定/人物.md"],
    ),
    {
      paths: ["设定/人物.md"],
      status: "errored",
      toolCallId: "call-write-1",
    },
  );
});

test("collectStudioWriteEffectsFromTurnResult reads write paths from structured output and resource links", () => {
  const effects = collectStudioWriteEffectsFromTurnResult({
    agent_id: null,
    client_turn_id: "turn-1",
    content: "已更新。",
    conversation_id: "conversation-1",
    hook_results: [],
    input_tokens: null,
    mcp_servers: [],
    model_name: "gpt-5.4",
    output_items: [
      {
        call_id: "call-read-1",
        item_id: "item-read-1",
        item_type: "tool_result",
        payload: {
          structured_output: {
            documents: [{ path: "设定/世界观.md" }],
          },
        },
        provider_ref: null,
        status: "completed",
      },
      {
        call_id: "call-write-1",
        item_id: "item-write-1",
        item_type: "tool_result",
        payload: {
          resource_links: [
            { path: "设定/人物.md" },
          ],
          structured_output: {
            document_ref: "file:设定/人物.md",
            path: "设定/人物.md",
          },
        },
        provider_ref: null,
        status: "completed",
        tool_name: "project.write_document",
      },
      {
        call_id: "call-edit-1",
        item_id: "item-edit-1",
        item_type: "tool_result",
        payload: {
          resource_links: [
            { path: "设定/时间轴.md" },
          ],
          structured_output: {
            document_ref: "file:设定/时间轴.md",
            path: "设定/时间轴.md",
          },
        },
        provider_ref: null,
        status: "completed",
        tool_name: "project.edit_document",
      },
    ],
    output_meta: {},
    output_tokens: null,
    provider: "openai",
    run_id: "run-1",
    skill_id: null,
    total_tokens: null,
  });

  assert.deepEqual(effects, [
    {
      paths: ["设定/人物.md"],
      status: "completed",
      toolCallId: "call-write-1",
    },
    {
      paths: ["设定/时间轴.md"],
      status: "completed",
      toolCallId: "call-edit-1",
    },
  ]);
});

test("isStudioAssistantWriteSuccessStatus treats committed write as effective", () => {
  assert.equal(isStudioAssistantWriteSuccessStatus("completed"), true);
  assert.equal(isStudioAssistantWriteSuccessStatus("committed"), true);
  assert.equal(isStudioAssistantWriteSuccessStatus("errored"), false);
});
