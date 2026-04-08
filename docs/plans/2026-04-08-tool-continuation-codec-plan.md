# 2026-04-08 Tool Continuation Codec Plan

> 状态：已完成（2026-04-08）

## 1. 背景

当前 shared runtime 已完成：

- `tool_name_codec.py`
- `tool_schema_compiler.py`
- conformance probe、`verified_probe_kind` 与 assistant capability gating

但 continuation projection 与 tool result 编码仍大量堆在 `llm_protocol_requests.py`，包括：

- runtime replay 文本投影
- OpenAI Chat / Claude / Gemini 的 continuation item 投影
- OpenAI Responses `function_call_output` 构造
- continuation tool name 收集与 `previous_response_id` 读取

这使 continuation 仍然贴近具体 request builder，而不是 shared interop 边界。

## 2. 目标

- 新增 shared `tool_continuation_codec.py`
- 把 continuation projection / tool result encoding / responses continuation input 构造收口到 interop 层
- 继续保持 assistant / verifier / probe 的 continuation 行为完全不变

## 3. 设计选择

- 这轮以“抽取而不改语义”为原则
- `tool_continuation_codec.py` 只负责 continuation 编码与投影，不改 `continuation_support` 判定
- `llm_protocol_requests.py` 保留 request builder 职责，只消费 codec 输出

## 4. 实施步骤

### Phase 1：codec 抽取

- 新增 `app/shared/runtime/llm/interop/tool_continuation_codec.py`
- 收口 text projection、OpenAI Chat / Anthropic / Gemini replay projection
- 收口 OpenAI Responses continuation input 与 continuation tool name 收集

### Phase 2：请求主链接入

- `llm_protocol_requests.py` 改为调用 codec
- 删除内联 continuation helper

### Phase 3：验证与文档

- 新增 codec 定向单测
- 补回 protocol/tool provider/assistant 相关回归
- 同步设计文档、`tools.md`、`memory.md`

## 5. 验证命令

```bash
cd apps/api && ./.venv/bin/pytest -q \
  tests/unit/test_tool_continuation_codec.py \
  tests/unit/test_llm_protocol_tool_calling.py \
  tests/unit/test_llm_tool_provider.py \
  tests/unit/test_provider_tool_conformance_support.py \
  tests/unit/test_assistant_service.py
```

## 6. 实施结果

- 已新增 `app/shared/runtime/llm/interop/tool_continuation_codec.py`
- `llm_protocol_requests.py` 当前已改为消费 codec，不再内联 continuation projection / tool result encoding / responses continuation input 构造
- 残余 dead continuation helpers 已从 `llm_protocol_requests.py` 清理
- continuation codec 定向与主链联合回归 `133 passed`
