# LiteLLM Southbound Integration Plan

| 字段 | 内容 |
|---|---|
| 文档类型 | 实施方案 |
| 文档状态 | 已完成 |
| 创建时间 | 2026-04-16 |
| 更新时间 | 2026-04-16 |
| 关联文档 | [22-assistant-tool-calling-runtime](../design/22-assistant-tool-calling-runtime.md)、[23-provider-tool-interop-compatibility-layer](../design/23-provider-tool-interop-compatibility-layer.md)、[模型协议兼容中间层重构方案](./2026-04-07-model-provider-compatibility-middleware-plan.md) |

## 1. 目标

把 easyStory 当前自研的 southbound provider transport 替换为以 LiteLLM 为主的 backend 分层，同时保留：

- assistant runtime 的 tool loop / run store / continuation 真值
- credential verifier 的 probe contract
- canonical tool name / schema / continuation item 语义
- project 本地工具执行权

## 2. 实施边界

本轮只替 southbound transport，不重写 assistant 业务层。

### 保留不动的上层真值

- `AssistantService / AssistantToolLoop`
- `project.*` 本地工具与授权策略
- credential scope / verify state / audit
- canonical tool id、continuation items、provider continuation support

### 替换的主路径

- `LLMToolProvider` 底层 provider 调用
- verifier / provider interop probe 的执行主链
- 直连 HTTP request/response/stream 在主路径中的直接耦合

## 3. 设计原则

1. `LiteLLM backend` 作为默认 southbound backend。
2. 对 LiteLLM 明显不适合硬吃的连接场景，保留显式 `native_http backend`，不做 silent fallback。
3. backend 选择必须由连接能力和请求特征决定，保持可解释。
4. 上层继续消费 `LLMGenerateRequest / NormalizedLLMResponse`，不把 LiteLLM 的对象泄漏到业务层。
5. 对外错误继续显式暴露，不通过降级隐藏问题。

## 4. 结构目标

```text
shared/runtime/llm/
  llm_backend.py              # backend protocol / resolver
  litellm_backend.py          # LiteLLM southbound backend
  native_http_backend.py      # 显式保留的原生 HTTP backend
  llm_tool_provider.py        # 只做参数校验 + backend 调度 + contract 映射
```

verifier / probe 侧目标：

- 不再把 `PreparedLLMHttpRequest` 作为主执行链真值
- probe 仍返回同一套 `text_probe / tool_definition_probe / tool_call_probe / tool_continuation_probe`
- interop 脚本与 verifier 共享 backend 主链

## 5. 分步实施

1. 新增 backend protocol，接通 LiteLLM 与显式 native_http backend。
2. 重构 `LLMToolProvider` 使用 backend。
3. 重构 verifier / provider interop probe 使用 backend。
4. 清理主路径中废弃的 direct HTTP glue。
5. 跑定向验证并同步文档。

## 6. 风险点

- LiteLLM 对任意 `custom_header` 鉴权、完整 endpoint `base_url`、自定义 Gemini 网关、自定义 OpenAI Responses 网关、`openai_responses + stop` 与部分 provider-native thinking 语义未必天然等价。
- 现有单测大量绑定 request JSON shape，需要按新 backend 分层重写。
- 真实渠道失败不能视为本轮代码回归，需和上游 provider 状态区分。
