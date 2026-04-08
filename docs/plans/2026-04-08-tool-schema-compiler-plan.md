# 2026-04-08 Tool Schema Compiler Plan

> 状态：已完成（2026-04-08）

## 1. 背景

当前 shared runtime 在本轮开始前已完成：

- tool name alias codec
- conformance probe
- `verified_probe_kind` 持久化与 assistant capability gating

但 tool schema 适配仍散落在协议请求 builder 中，尤其：

- OpenAI / Claude 直接透传 `tool.parameters`
- Gemini 在 `llm_protocol_requests.py` 内部做局部 sanitize

这会导致协议边界继续承载 provider-specific schema 细节，后续增加 gateway profile 时维护成本高，也容易再次出现“某家能用、另一家挂掉”的漂移。

## 2. 目标

- 新增 shared `tool_schema_compiler.py`
- 把 portable schema 编译逻辑从 builder 中抽离
- 通过 `LLMInteropCapabilities.tool_schema_mode` 显式表达 schema 编译策略
- 统一 assistant / verifier / interop probe 走同一条 schema 编译主链

## 3. 设计选择

- 新增 `ToolSchemaMode`
- 第一轮支持：
  - `portable_subset`
  - `gemini_compatible`
- `portable_subset` 负责把“required-only anyOf” 收口为可移植描述，不再把这类 schema 直接暴露给外部协议
- `gemini_compatible` 在 `portable_subset` 基础上继续移除 Gemini 不支持的 schema key
- 当前默认 profile 先全部走共享 compiler；其中 Gemini 走更严格的 `gemini_compatible`

## 4. 实施步骤

### Phase 1：compiler 与 capability

- 新增 `app/shared/runtime/llm/interop/tool_schema_compiler.py`
- `LLMInteropCapabilities` 增加 `tool_schema_mode`
- `resolve_interop_capabilities()` 为各协议族返回明确 schema mode

### Phase 2：请求主链接入

- `llm_protocol_requests.py` 不再内联 Gemini sanitize
- OpenAI Responses / Chat、Anthropic、Gemini 全部通过 compiler 构造工具 schema

### Phase 3：验证与文档

- 补齐 compiler / interop profile / protocol request 定向单测
- 同步设计文档、`tools.md`、`memory.md`

## 5. 验证命令

```bash
cd apps/api && ./.venv/bin/pytest -q \
  tests/unit/test_tool_schema_compiler.py \
  tests/unit/test_llm_protocol_tool_calling.py \
  tests/unit/test_llm_interop_profiles.py \
  tests/unit/test_llm_tool_provider.py
```

## 6. 实施结果

- 已新增 `app/shared/runtime/llm/interop/tool_schema_compiler.py`
- `LLMInteropCapabilities` 已新增 `tool_schema_mode`
- OpenAI Responses / Chat、Anthropic、Gemini 的 tool definitions 已统一走 compiler
- `portable_subset` 现用于共享可移植 schema，`gemini_compatible` 在其基础上继续移除 Gemini 不支持的 key
- 定向 schema/compiler 回归 `52 passed`
- 联合 verifier / provider interop / assistant 回归 `110 passed`
