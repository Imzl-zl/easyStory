# 模型工具调用兼容层实施计划

| 字段 | 内容 |
|---|---|
| 文档类型 | 实施方案 |
| 文档状态 | 主干实施完成 |
| 创建时间 | 2026-04-08 |
| 更新时间 | 2026-04-08 |
| 关联文档 | [模型工具调用兼容层设计](../design/23-provider-tool-interop-compatibility-layer.md)、[Assistant 原生 Tool-Calling Runtime](../design/22-assistant-tool-calling-runtime.md)、[模型协议兼容中间层重构方案](./2026-04-07-model-provider-compatibility-middleware-plan.md) |

---

## 1. 目标

把 `docs/design/23-provider-tool-interop-compatibility-layer.md` 的长期设计，拆成可渐进落地、但每一阶段都稳定可维护的实施闭环。  
本轮优先级不是“最少改动”，而是先建立**内部 canonical tool contract 与外部协议 tool name contract 的正式边界**，避免 assistant、probe、verifier 再重复踩同一类协议问题。

## 2. 当前根因

`2026-04-08` 自测已经确认：

- 内部 canonical tool name 目前使用 dotted name，例如 `project.search_documents`
- 该名字在 OpenAI-compatible 请求里被直接外发
- `bwen/gpt-5.4` 这类上游对 tool/function name 执行安全字符校验，导致 tool-calling 失败
- Gemini 当前能跑通，只说明它对该名字更宽容，不代表当前边界设计正确

因此本轮实施必须先修正：

1. 请求构造的外部 tool name 编码
2. runtime replay 中 tool call / tool result 的外部 tool name 编码
3. 响应解析与流式终态解析中的外部 tool name -> canonical tool name 回收
4. capability profile 中与 tool name policy 相关的共享能力描述

## 3. 实施原则

- 内部 canonical tool id 继续保留 dotted name
- 外部协议统一使用安全 alias
- alias 逻辑放在 `shared/runtime/llm/interop`，不下沉到 assistant 业务域
- 现有 `interop_profile` 不再只描述 stream 差异，要开始承载 tool name policy 这种协议边界能力
- 不增加静默 fallback；协议不兼容就显式失败

## 4. 分阶段计划

### Phase 1：Tool Name Codec 基础层

目标：

- 新增 `tool_name_codec.py`
- 定义 canonical tool name -> external safe alias 的稳定映射
- 支持反向恢复 external alias -> canonical tool name
- 处理冲突、长度限制和不可逆字符

完成标准：

- codec 单独可测
- 当前 `project.*` 工具能稳定映射成安全 ASCII 名

### Phase 2：协议请求/响应主链接入

目标：

- `llm_protocol_requests.py` 外发 tools 时统一使用 alias
- OpenAI Chat / Claude / Gemini runtime replay 时，tool call / tool result 一律编码成外部 alias
- `llm_protocol_responses.py` 和 `llm_stream_events.py` 在解析 tool call 时恢复 canonical tool name
- `PreparedLLMHttpRequest` 保留本次请求的 alias 真值，避免流式和非流式出现双真值

完成标准：

- assistant 内部仍只看到 canonical tool name
- 外部请求与上游返回的工具名已与内部真值解耦

### Phase 3：Capability Profile 收口

目标：

- 扩展 `LLMInteropCapabilities`
- 补入 `tool_name_policy` 等协议边界能力
- 保持现有 stream/profile 行为不回归

完成标准：

- profile 解析仍然稳定
- tool name policy 已通过共享 capability 暴露，而不是散点判断

### Phase 4：验证与回归

目标：

- 补齐 tool alias 单测
- 覆盖请求编码、runtime replay、响应解码、stream terminal 解码
- 对 provider interop / verifier 保持兼容

完成标准：

- 定向单测通过
- 不引入 assistant/tool calling 主链回归

## 5. 首轮实施边界

本轮最初落地到代码的目标是完成 `Phase 1 + Phase 2 + Phase 3`，并补齐 `Phase 4` 的定向回归。  
后续轮次已继续完成 conformance probes、Credential Center 显式 `验证连接 / 验证工具`、`verified_probe_kind` 持久化、assistant capability gating，以及 shared `tool_schema_compiler` 收口；本节保留为 tool name alias 首轮实施边界记录。

## 5.1 本轮实施结果

截至 `2026-04-08`，本轮已完成：

- `tool_name_codec.py` 已落地
- `PreparedLLMHttpRequest` 已携带 `tool_name_aliases`
- `llm_protocol_requests / responses / stream_events / llm_tool_provider` 已打通 alias 编码与解码
- `LLMInteropCapabilities` 已补 `tool_name_policy`
- 定向回归已通过，累计 `85 passed`

后续同日补充完成的相关轮次见：

- [2026-04-08-provider-tool-conformance-probes-plan](./2026-04-08-provider-tool-conformance-probes-plan.md)
- [2026-04-08-credential-interop-profile-plumbing-plan](./2026-04-08-credential-interop-profile-plumbing-plan.md)
- [2026-04-08-credential-tool-verify-productization-plan](./2026-04-08-credential-tool-verify-productization-plan.md)
- [2026-04-08-assistant-tool-capability-gating-plan](./2026-04-08-assistant-tool-capability-gating-plan.md)
- [2026-04-08-tool-schema-compiler-plan](./2026-04-08-tool-schema-compiler-plan.md)

## 5.2 同日后续主干收口

截至 `2026-04-08` 当天收尾，本条兼容层主线已经继续完成以下 shared runtime 模块与产品闭环：

- `provider_tool_conformance_support.py`
  - 共享 `text_probe / tool_definition_probe / tool_call_probe / tool_continuation_probe`
- `ModelCredential.interop_profile`
  - 凭证模型、verifier、assistant runtime、Credential Center 共用同一份协议兼容真值
- `ModelCredential.verified_probe_kind`
  - 保存“当前最高已证明 capability”，assistant visible tools 显式要求 `tool_continuation_probe`
- `tool_schema_compiler.py`
  - OpenAI / Claude / Gemini tool schema 统一编译
- `tool_continuation_codec.py`
  - runtime replay projection、tool result encoding 与 OpenAI Responses continuation input 已统一抽离
- `tool_call_codec.py`
  - response / stream terminal 的 tool call parse、alias reverse decode、invalid arguments recovery 已统一抽离
- `stream_event_normalizer.py`
  - OpenAI Chat / Responses、Anthropic、Gemini 的 `delta / reasoning_delta / stop_reason / terminal payload` 已统一抽离
- Credential Center
  - 已显式区分 `验证连接(text_probe)` 与 `验证工具(tool_continuation_probe)`

这意味着这条兼容层主线已经不再停留在“tool name alias 热修”，而是完成了 request / response / stream / continuation / verification / product entry 的 shared runtime 主干收口。

相关子计划：

- [2026-04-08-provider-tool-conformance-probes-plan](./2026-04-08-provider-tool-conformance-probes-plan.md)
- [2026-04-08-credential-interop-profile-plumbing-plan](./2026-04-08-credential-interop-profile-plumbing-plan.md)
- [2026-04-08-credential-tool-verify-productization-plan](./2026-04-08-credential-tool-verify-productization-plan.md)
- [2026-04-08-assistant-tool-capability-gating-plan](./2026-04-08-assistant-tool-capability-gating-plan.md)
- [2026-04-08-tool-schema-compiler-plan](./2026-04-08-tool-schema-compiler-plan.md)
- [2026-04-08-tool-continuation-codec-plan](./2026-04-08-tool-continuation-codec-plan.md)
- [2026-04-08-tool-call-codec-plan](./2026-04-08-tool-call-codec-plan.md)
- [2026-04-08-stream-event-normalizer-plan](./2026-04-08-stream-event-normalizer-plan.md)

## 6. 收尾验证命令

```bash
cd apps/api && ./.venv/bin/pytest -q tests/unit/test_llm_protocol_tool_calling.py tests/unit/test_llm_interop_profiles.py tests/unit/test_llm_tool_provider.py tests/unit/test_provider_interop_support.py tests/unit/test_provider_interop_check.py tests/unit/test_credential_verifier.py tests/unit/test_provider_interop_stream_support.py tests/unit/test_llm_stream_completion.py
```

```bash
cd apps/api && ./.venv/bin/pytest -q \
  tests/unit/test_tool_schema_compiler.py \
  tests/unit/test_tool_continuation_codec.py \
  tests/unit/test_tool_call_codec.py \
  tests/unit/test_stream_event_normalizer.py \
  tests/unit/test_provider_tool_conformance_support.py \
  tests/unit/test_llm_protocol_tool_calling.py \
  tests/unit/test_llm_interop_profiles.py \
  tests/unit/test_llm_tool_provider.py \
  tests/unit/test_provider_interop_support.py \
  tests/unit/test_provider_interop_check.py \
  tests/unit/test_provider_interop_stream_support.py \
  tests/unit/test_llm_stream_completion.py \
  tests/unit/test_credential_verifier.py \
  tests/unit/test_credential_service.py \
  tests/unit/test_credential_service_updates.py \
  tests/unit/test_credential_api.py \
  tests/unit/test_assistant_service.py
```

```bash
pnpm --dir apps/web test:unit -- --runInBand \
  src/features/settings/components/credential-center-action-support.test.ts \
  src/features/settings/components/credential-center-feedback.test.ts \
  src/features/settings/components/credential-center-display-support.test.ts \
  src/features/settings/components/credential-center-support.test.ts
```

```bash
pnpm --dir apps/web lint
```

## 7. 收尾验证结果

- 后端：
  - `ruff check ...` 通过
  - `pytest -q ...` 通过，`230 passed in 25.72s`
- 前端：
  - `pnpm --dir apps/web test:unit -- --runInBand ...` 通过，runner 实际执行 support suite，`62 passed`
  - `pnpm --dir apps/web lint` 通过
