# 2026-04-08 Stream Event Normalizer Plan

## 1. 背景

当前 shared runtime 已完成：

- `tool_name_codec.py`
- `tool_schema_compiler.py`
- `tool_call_codec.py`
- `tool_continuation_codec.py`

但流式协议归一化仍主要放在 `llm_stream_events.py`，包括：

- 各协议 `delta` 提取
- `reasoning_delta` 提取
- `stop_reason` 归一化
- terminal payload 提取与终态 response 解析

这说明 stream 协议边界还没有像 request / response / continuation 一样完全收口到 `interop` 层。

## 2. 目标

- 新增 shared `stream_event_normalizer.py`
- 把协议级 stream event parse 收口到 interop 层
- 保持 `parse_raw_stream_event()`、`provider_interop_stream_support.py`、`llm_tool_provider.execute_stream()` 当前行为不变

## 3. 设计选择

- 本轮只抽取 stream normalizer，不扩大到 transport 或 terminal assembly
- `llm_stream_events.py` 保留 facade 职责，只消费 interop normalizer
- terminal response 继续通过 `parse_stream_terminal_response()` 走既有 response codec

## 4. 实施步骤

### Phase 1：normalizer 抽取

- 新增 `app/shared/runtime/llm/interop/stream_event_normalizer.py`
- 收口 `delta / reasoning_delta / stop_reason / truncation / terminal payload` 解析

### Phase 2：主链接入

- `llm_stream_events.py` 改为调用 shared normalizer
- 保持 `ParsedStreamEvent` dataclass 与现有公开接口不变

### Phase 3：验证与文档

- 补齐 normalizer 定向单测
- 跑 stream completion / provider interop stream support / tool calling 联合回归
- 同步设计文档、`tools.md`、`memory.md`

## 5. 验证命令

```bash
cd apps/api && ./.venv/bin/pytest -q \
  tests/unit/test_stream_event_normalizer.py \
  tests/unit/test_provider_interop_stream_support.py \
  tests/unit/test_llm_stream_completion.py \
  tests/unit/test_llm_protocol_tool_calling.py
```

## 6. 实施结果

- 已新增 `apps/api/app/shared/runtime/llm/interop/stream_event_normalizer.py`
- `llm_stream_events.py` 已降为 facade，只转发 shared normalizer 的公开接口
- OpenAI Chat / Responses、Anthropic、Gemini 的 `delta / reasoning_delta / stop_reason / truncation / terminal payload` 协议分支已统一收口
- terminal response 仍通过 `parse_stream_terminal_response()` 复用既有 response codec，没有引入第二套终态解析真值
- 已新增 `apps/api/tests/unit/test_stream_event_normalizer.py`，直测 normalizer 自身契约

## 7. 验证结果

- `cd apps/api && ./.venv/bin/ruff check app/shared/runtime/llm/interop/stream_event_normalizer.py app/shared/runtime/llm/llm_stream_events.py tests/unit/test_stream_event_normalizer.py`
- `cd apps/api && ./.venv/bin/pytest -q tests/unit/test_stream_event_normalizer.py tests/unit/test_provider_interop_stream_support.py tests/unit/test_llm_stream_completion.py tests/unit/test_llm_protocol_tool_calling.py tests/unit/test_llm_interop_profiles.py`
- 结果：`42 passed`
