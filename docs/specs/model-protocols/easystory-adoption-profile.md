# easyStory 采用映射

| 字段 | 内容 |
|---|---|
| 文档类型 | 项目映射 / 实施真值 |
| 文档状态 | 生效 |
| 创建时间 | 2026-04-10 |
| 更新时间 | 2026-04-10 |
| 关联文档 | [模型协议与工具调用标准](./README.md)、[Assistant 原生 Tool-Calling Runtime 设计](../../design/22-assistant-tool-calling-runtime.md)、[模型工具调用兼容层设计](../../design/23-provider-tool-interop-compatibility-layer.md) |

---

## 1. 作用

本文只记录 easyStory 当前如何采用本目录里的通用标准。

也就是说：

- 通用协议事实和跨项目建议，看本目录其他文档
- easyStory 当前字段名、默认值、UI 验证动作、项目工具面，看本文

## 2. 当前协议族与 profile

当前代码只支持：

- `openai_responses`
- `openai_chat_completions`
- `anthropic_messages`
- `gemini_generate_content`

当前 `interop_profile` 只用于：

- `responses_strict`
- `responses_delta_first_terminal_empty_output`
- `chat_compat_plain`
- `chat_compat_reasoning_content`
- `chat_compat_usage_extra_chunk`

其中：

- `openai_responses` 默认 profile 是 `responses_delta_first_terminal_empty_output`
- `openai_chat_completions` 默认 profile 是 `chat_compat_plain`

## 3. 当前连接与验证字段名

easyStory 当前连接真值对象使用这些字段：

- `api_dialect`
- `auth_strategy`
- `api_key_header_name`
- `user_agent_override`
- `client_name`
- `client_version`
- `runtime_kind`
- `context_window_tokens`
- `default_max_output_tokens`

工具能力验证真值当前落在：

- `last_verified_at`
  - 仅文本连接
- `stream_tool_verified_probe_kind`
  - 流式工具能力
- `buffered_tool_verified_probe_kind`
  - 非流工具能力

## 4. Credential Center 当前产品动作

当前前端显式区分：

- `验证连接`
  - `text_probe`
- `验证流式工具`
  - `tool_continuation_probe + transport_mode=stream`
- `验证非流工具`
  - `tool_continuation_probe + transport_mode=buffered`

assistant runtime 会根据本轮是否开启流式，选择对应一侧的工具能力真值。

## 5. 当前请求构造实现差异

当前实现里有几条需要记住的 easyStory 采用策略：

- OpenAI Chat
  - 官方 `api.openai.com` 用 `max_completion_tokens`
  - 兼容网关默认回退 `max_tokens`
- Anthropic
  - 若业务层未显式设置输出上限，会按 `context_window_tokens` 计算默认 `max_tokens`
- Gemini
  - 当前代码使用 `generationConfig / toolConfig`
  - `system_instruction` 采用当前上游可接受的请求形态

## 6. 当前 project.* 工具面

当前 assistant descriptor registry 只暴露 4 个项目工具：

- `project.list_documents`
- `project.search_documents`
- `project.read_documents`
- `project.write_document`

其中：

- 前 3 个是只读资源工具
- `project.write_document` 是写工具，采用 `grant_bound`

## 7. 当前写工具可见前提

`project.write_document` 当前只有在满足以下条件时才会 visible：

- 在项目作用域内
- `requested_write_scope == "turn"`
- 仅有一个允许目标文稿
- 允许目标与 active document 一致
- active binding 可写
- active buffer state 能提取可信快照

执行时还会再次校验：

- grant 存在
- tool name、target、binding version 一致
- trusted snapshot 的 `base_version / buffer_hash / source` 一致

## 8. 当前 Gemini 流式实践

easyStory 当前已补齐 Gemini 流式 tool-call synthesize。

原因是：

- 早期 SSE 事件里可能已经有 `functionCall`
- 最后一个 payload 可能没有文本
- 如果只看 terminal payload，会误判“空响应”或重复 tool call

因此当前实现会：

- 累积整个流里出现过的 `functionCall`
- 最终再合并到 terminal payload
- 按 `id` 或 `name + args` 去重

## 9. 当前代码定位

若要看实现真值，关键文件在：

- `apps/api/app/shared/runtime/llm/llm_protocol_types.py`
- `apps/api/app/shared/runtime/llm/llm_protocol_requests.py`
- `apps/api/app/shared/runtime/llm/llm_protocol_responses.py`
- `apps/api/app/shared/runtime/llm/interop/stream_event_normalizer.py`
- `apps/api/app/shared/runtime/llm/interop/gemini_stream_synthesizer.py`
- `apps/api/app/modules/assistant/service/tooling/assistant_tool_registry.py`
- `apps/api/app/modules/credential/service/credential_verification_support.py`

## 10. 边界

本文是 easyStory 项目映射。  
如果你要把整套文档拿去别的项目复用，优先看本目录其他 5 篇标准文档，不要直接把这里的字段名和产品动作复制过去。
