# Provider Tool Conformance Probes 实施计划

| 字段 | 内容 |
|---|---|
| 文档类型 | 实施方案 |
| 文档状态 | 首轮实施完成 |
| 创建时间 | 2026-04-08 |
| 更新时间 | 2026-04-08 |
| 关联文档 | [模型工具调用兼容层设计](../design/23-provider-tool-interop-compatibility-layer.md)、[模型工具调用兼容层实施计划](./2026-04-08-provider-tool-interop-implementation-plan.md) |

---

## 1. 目标

在上一轮 alias 边界已经打稳的前提下，继续把设计文档里定义的 conformance probe 往前落地。  
这一轮的目标不是直接改 UI 或 credential 验证接口，而是先把四类 probe 的共享执行语义实现出来，让 `provider_interop_check` 先成为正式探测入口。

## 2. 范围

本轮实现：

- `text_probe`
- `tool_definition_probe`
- `tool_call_probe`
- `tool_continuation_probe`

本轮暂不实现：

- 凭证页多 probe 结果展示
- assistant 产品侧 capability gating
- probe 结果持久化

## 3. 设计约束

- 所有 probe 都必须复用现有 `LLMGenerateRequest -> PreparedLLMHttpRequest -> parse_generation_response / execute_stream_probe_request` 主链
- `tool_call_probe` 和 `tool_continuation_probe` 必须使用内部 canonical dotted tool name，再通过 alias codec 对外发安全名
- `tool_continuation_probe` 必须复用现有 continuation_items / provider_continuation_state 语义，而不是单独造旁路协议

## 4. 实施步骤

### Phase 1：共享 probe support

- 新增 shared runtime support 模块
- 固定 probe 工具契约、初始 prompt、follow-up prompt
- 统一构造 continuation_items 与 provider_continuation_state
- 固定校验规则

### Phase 2：CLI 接入

- `provider_interop_check.py` 新增 `--probe-kind`
- 默认仍为 `text_probe`
- `tool_continuation_probe` 支持两轮请求执行与输出汇总

### Phase 3：验证

- 补充 support 单测
- 更新 CLI parser / 执行路径测试
- 跑定向 pytest 与至少一次本地 dry-run

## 5. 验证命令

```bash
cd apps/api && ./.venv/bin/pytest -q tests/unit/test_provider_tool_conformance_support.py tests/unit/test_provider_interop_check.py tests/unit/test_provider_interop_support.py tests/unit/test_llm_protocol_tool_calling.py tests/unit/test_llm_interop_profiles.py tests/unit/test_credential_verifier.py
```

## 6. 本轮实施结果

截至 `2026-04-08`，本轮已完成：

- `shared/runtime/llm/interop/provider_tool_conformance_support.py` 已落地
- `provider_interop_check.py` 已支持 `--probe-kind`
- 当前支持 `text_probe / tool_definition_probe / tool_call_probe / tool_continuation_probe`
- 定向单测 `56 passed`
- dry-run 已确认 staged request 形状正确
- 真实 `gpt` profile 探测已显式暴露：
  - `tool_call_probe initial stage failed: Probe failed with HTTP 502`
  - `tool_continuation_probe initial stage failed: output must be a non-empty list`

这些现象说明：共享 probe 基座已经可以工作，但当前 `gpt` profile 对真实 tool contract 的支持仍不稳定，问题已经被正式收口到 conformance probe 层显式暴露。
