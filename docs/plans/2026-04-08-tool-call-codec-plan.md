# 2026-04-08 Tool Call Codec Plan

## 1. 背景

当前 shared runtime 已完成：

- `tool_name_codec.py`
- `tool_schema_compiler.py`
- `tool_continuation_codec.py`

但 response / stream 侧的 tool call 解析仍主要放在 `llm_protocol_responses.py`，包括：

- alias 反向恢复
- `arguments_text / arguments_error` 归一化
- OpenAI / Anthropic / Gemini tool call 提取

这说明 parse 边界还没有和 request/continuation 一样完全收口到 interop 层。

## 2. 目标

- 新增 shared `tool_call_codec.py`
- 把 tool call 解析、arguments 归一化、tool name alias 回收收口到 interop 层
- 保持 `parse_generation_response / parse_stream_terminal_response / parse_raw_stream_event` 行为不变

## 3. 设计选择

- 这轮只收口 tool call parse codec，不扩大到 text/reasoning/refusal item 编码
- `llm_protocol_responses.py` 保留 response assembly 职责，只消费 codec 返回的 `NormalizedLLMToolCall`
- 流式 terminal path 继续通过 `parse_stream_terminal_response()` 复用同一条 parse codec

## 4. 实施步骤

### Phase 1：codec 抽取

- 新增 `app/shared/runtime/llm/interop/tool_call_codec.py`
- 收口 alias reverse decode、arguments parse、`NormalizedLLMToolCall` 构造
- 收口 OpenAI Chat / Responses、Anthropic、Gemini 的 tool call 提取

### Phase 2：response / stream 主链接入

- `llm_protocol_responses.py` 改为调用 codec
- 清理内联 tool call parse helpers

### Phase 3：验证与文档

- 新增 codec 定向单测
- 补回 response / stream / provider interop 定向回归
- 同步设计文档、`tools.md`、`memory.md`

## 5. 验证命令

```bash
cd apps/api && ./.venv/bin/pytest -q \
  tests/unit/test_tool_call_codec.py \
  tests/unit/test_llm_protocol_tool_calling.py \
  tests/unit/test_llm_interop_profiles.py \
  tests/unit/test_provider_interop_stream_support.py \
  tests/unit/test_llm_stream_completion.py
```

## 6. 实施结果

- 已新增 `apps/api/app/shared/runtime/llm/interop/tool_call_codec.py`
- `llm_protocol_responses.py` 已改为通过 codec 统一解析 OpenAI Chat / Responses、Anthropic、Gemini 的 tool call
- `parse_generation_response()` 与 `parse_stream_terminal_response()` 现统一接收 `tool_name_aliases`，response / stream terminal 路径共用同一套 alias reverse decode 与参数归一化语义
- 原先散落在 `llm_protocol_responses.py` 的内联 tool call parse helpers 已删除
- 已新增 `apps/api/tests/unit/test_tool_call_codec.py`，直测 codec 自身契约

## 7. 验证结果

- `cd apps/api && ./.venv/bin/ruff check app/shared/runtime/llm/interop/tool_call_codec.py app/shared/runtime/llm/llm_protocol_responses.py tests/unit/test_tool_call_codec.py`
- `cd apps/api && ./.venv/bin/pytest -q tests/unit/test_tool_call_codec.py tests/unit/test_llm_protocol_tool_calling.py tests/unit/test_llm_interop_profiles.py tests/unit/test_provider_interop_stream_support.py tests/unit/test_llm_stream_completion.py`
- 结果：`44 passed`
