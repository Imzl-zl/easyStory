# 主流模型厂商响应结构与流式事件参考

| 字段 | 内容 |
|---|---|
| 文档类型 | 技术规范 / 响应契约参考 |
| 文档状态 | 生效 |
| 创建时间 | 2026-04-02 |
| 更新时间 | 2026-04-04 |
| 关联文档 | [主流模型厂商请求参数参考](./model-provider-request-params-reference.md)、[主流模型厂商请求头与客户端标识参考](./model-provider-client-identity-and-headers-reference.md)、[技术栈确定](./tech-stack.md) |

---

## 1. 适用范围

本文补充 `OpenAI GPT / Anthropic Claude / Google Gemini / Moonshot Kimi / MiniMax / Zhipu GLM / DeepSeek` 的非流式响应体、流式 SSE 事件、`usage` 返回位置和关键返回头，供 easyStory 做 provider interop、流式解析和排错时参考。

使用原则：

- 只采纳官方文档、官方 API 参考和官方示例。
- 把“请求参数”“响应契约”“请求头 / 客户端标识”分开建模，不混成一个大兼容层。
- 返回头主要用于排错和观测，不替代响应体解析。
- 对官方未系统列出的返回头，只记录官方明确写出的字段，不做经验性扩展。
- 当前 easyStory runtime 原生流式 / 非流式 parser 只覆盖 `openai_responses / openai_chat_completions / anthropic_messages / gemini_native` 四类；`Kimi / MiniMax / GLM / DeepSeek` 目前主要作为 `openai_chat_completions` 家族的参考资料。

---

## 2. 先看结论

- 真正最容易导致解析错误的，通常不是请求头，而是响应体结构和流式事件语义。
- OpenAI 现在对新项目推荐 `Responses API`，但 `Chat Completions` 仍受支持；两者必须按两套响应契约处理。
- Claude 的流式不是 `delta.content` 这一类通用 chunk，而是具名事件序列。
- Gemini 原生接口和 Gemini OpenAI 兼容层的响应结构完全不同，不能共用一个提取器。
- Kimi / MiniMax / GLM / DeepSeek 虽然都长得像 OpenAI Chat Completions，但 `reasoning_content`、`usage` 和流式结束信号并不完全等价。
- 返回头应该收集，但主要用于请求追踪、限流排查和性能观测，不要把它当主解析真值。

---

## 3. 一页总览

| 厂商 / 方言 | 非流式文本提取 | 流式增量提取 | 完成信号 | `usage` 位置 | 官方明确返回头 |
|---|---|---|---|---|---|
| OpenAI `responses` | `output_text` 或 `output[]` | `response.output_text.delta` | `response.completed` | 完成事件 / 最终响应对象 | `x-request-id`、`x-ratelimit-*`、`openai-processing-ms`、`openai-version`、`openai-organization` |
| OpenAI `chat/completions` | `choices[0].message.content` | `choices[0].delta.content` | `data: [DONE]` | 最终响应；带 `include_usage` 时可有附加块 | 同上 |
| Claude `messages` | `content[]` 文本块 | `content_block_delta` | `message_stop` | `message_start` 初始计数 + `message_delta` 累积计数 | `request-id`、`anthropic-organization-id` |
| Gemini 原生 | `candidates[0].content.parts[]` | `GenerateContentResponse` SSE / SDK chunk | 流结束 | 完整响应对象 | 官方未单列通用返回头 |
| Gemini OpenAI 兼容层 | `choices[0].message.content` | OpenAI 风格 chunk | `data: [DONE]` | 兼容层最终块 | 官方未单列通用返回头 |
| Kimi | `choices[0].message.content` | `choices[0].delta.content` / `choices[0].delta.reasoning_content` | `data: [DONE]` | 最终响应或 `include_usage` 附加块 | 官方未单列通用返回头 |
| MiniMax 原生 | `choices[0].message.content` | `choices[0].delta.content` | `data: [DONE]` | 最终块 | 官方未单列通用返回头 |
| GLM | `choices[0].message.content` | `choices[0].delta.content` / `choices[0].delta.reasoning_content` | `data: [DONE]` | 最终块 | 官方未单列通用返回头 |
| DeepSeek | `choices[0].message.content` + `reasoning_content` | `choices[0].delta.content` / `choices[0].delta.reasoning_content` | `data: [DONE]` | 最终块；`include_usage` 时在 `[DONE]` 前有额外 usage 块 | 官方未单列通用返回头 |

工程结论：

- 解析层至少要区分 `openai_responses / anthropic_messages / gemini_native / openai_chat_completions` 四大类。
- `openai_chat_completions` 下面再细分 `reasoning_content` 是否独立回传。
- “请求能发出去”和“响应能正确解析”是两件事，必须分别建测试。
- easyStory 当前运行时代码也确实是按这四类建 parser；如果后续要把 `Kimi / MiniMax / GLM / DeepSeek` 做成 vendor-native dialect，需要新增独立的请求 builder、SSE parser 和测试，不要只补文档。

---

## 4. OpenAI：Responses 与 Chat Completions 的真正区别

截至 `2026-04-02`，OpenAI 官方文档明确写的是：

- `Responses API` 推荐用于所有新项目。
- `Chat Completions` 仍受支持。
- `Responses API` 是 `Chat Completions` 的超集，可以渐进迁移。

这意味着 easyStory 里不能把 OpenAI 简化成一句“现在只剩 `/v1/responses`”，也不能继续把 `Responses` 当成老 `choices[]` 结构去解析。

### 4.1 非流式响应

`Responses API` 重点看：

- `output_text`
- `output[]`
- `status`
- `incomplete_details`
- `usage`

`Chat Completions` 重点看：

- `choices[0].message.content`
- `choices[0].finish_reason`
- `usage`

### 4.2 流式响应

`Responses API` 是语义化 SSE 事件，不是传统 `[DONE]` 收尾：

- `response.created`
- `response.output_text.delta`
- `response.completed`
- `error`

`Chat Completions` 仍是传统 OpenAI 风格 chunk：

- `choices[0].delta.content`
- `choices[0].delta.tool_calls`
- `data: [DONE]`

工程补充口径：

- 流式实现要把“传输层 SSE reader”和“协议层事件状态机”分开处理；前者负责稳定读完整条流，后者负责解析 `delta / completed / usage`。
- `Responses` 的渐进文本默认从 `response.output_text.delta` 累计；最终完成态以 `response.completed` 携带的 `response` 对象为准。
- 即使本次流式没有任何 `delta`，只要 `response.completed.response.output[]` 里有可提取文本，也应判定为成功，不应误报“无文本”。
- `usage` 优先从 `response.completed.response.usage` 或最终响应对象提取，不要把“有无 delta”当成 `usage` 是否可用的前提。
- 对 `Responses` 而言，`[DONE]` 最多是传输层收尾标记，不是业务上的“完成真值”；完成真值仍应看 `response.completed`。

### 4.3 解析层该怎么建模

- `openai_responses`：按事件名驱动状态机，最终从 `response.completed` 或最终响应对象收束。
- `openai_chat_completions`：按 `choices[].delta` 追加文本和工具调用，遇到 `[DONE]` 结束。
- 这两套不要强行揉成一个“OpenAI parser”。

---

## 5. 各厂商响应解析注意事项

### 5.1 OpenAI GPT

- 新项目推荐 `Responses API`，但兼容层仍要保留 `Chat Completions` 支持。
- `Responses API` 的 `output_text` 适合作为高层快捷提取；底层仍建议保留 `output[]` 原始块，避免丢失工具调用或多模态信息。
- `Responses` 流式不能再用“等 `[DONE]`”的旧逻辑。
- `Responses` 流式 reader 不应使用“短超时 + 取消底层读流”的实现；轮询超时只应用于断连检查，不应导致 `aiter_lines()` 一类底层 reader 被取消。
- 若代理或兼容层把完整文本和 `usage` 只放在 `response.completed.response` 中，解析器仍要从终态 payload 收束最终文本与统计值。

### 5.2 Anthropic Claude

- 流式事件主流程是 `message_start -> content_block_start -> content_block_delta -> content_block_stop -> message_delta -> message_stop`。
- `message_delta.usage` 是累计值，不是“本块增量”。
- thinking 场景下会有 `thinking_delta` 和 `signature_delta`。
- tool use 输入参数可能以 `input_json_delta` 形式逐块到达，必须累计后再做 JSON 解析。

### 5.3 Google Gemini

- 原生 `generateContent` 最稳的文本提取通常是 `candidates[0].content.parts[]`。
- 官方也明确说 SDK `chat` 本质只是 `generateContent` 的封装，每轮仍会把完整历史送回模型。
- 原生流式是 `streamGenerateContent?alt=sse` 或 SDK `generateContentStream`。
- 如果走 Gemini OpenAI 兼容层，才能按 `choices[0].message.content` 那套解析。

### 5.4 Moonshot Kimi

- 非流式结构与 OpenAI Chat Completions 很像，文本通常在 `choices[0].message.content`。
- thinking 模型会单独返回 `reasoning_content`，而且流式时 `reasoning_content` 会先于 `content`。
- 如果开启 `stream_options.include_usage`，会在结束前额外给出 usage 块；流被中断时可能没有最终 usage。
- 同一轮多次 tool call 的子回合里，要保留 `reasoning_content` 上下文。

### 5.5 MiniMax

- 原生接口是 `/v1/text/chatcompletion_v2`，并不是简单的 OpenAI 兼容壳。
- 原生示例里可见 `message.reasoning_content`。
- 如果走 OpenAI 兼容层，官方额外提供 `extra_body.reasoning_split=true`，可把推理拆到 `reasoning_details`。
- 所以 `MiniMax 原生` 和 `MiniMax OpenAI 兼容` 最好分成两个解析分支。

### 5.6 Zhipu GLM

- 整体外形接近 OpenAI Chat Completions。
- 流式示例里会分别返回 `delta.content` 和 `delta.reasoning_content`。
- `tool_stream` 是请求开关，响应解析端仍要准备处理普通文本 delta 和工具 / reasoning delta 混合到达。

### 5.7 DeepSeek

- 非流式返回里官方明确有 `content`、`reasoning_content`、`tool_calls`。
- 流式时 `delta.reasoning_content` 和 `delta.content` 需要分轨累计。
- 开启 `include_usage` 时，会在 `[DONE]` 前多一个 usage 统计块。
- DeepSeek 官方还明确说 `/v1` 只是兼容别名，不代表新的协议族。

---

## 6. 返回头该怎么用

先说结论：要收集，但别指望它解决主解析问题。

返回头适合做这些事：

- 记录上游请求 ID，便于找厂商支持或串联自家日志。
- 记录限流窗口和剩余额度，便于做 rate limit 诊断。
- 记录服务端处理耗时，区分“模型慢”还是“网络慢”。

不适合做这些事：

- 判断某段文本是不是完整回复。
- 推断是否有 tool call。
- 推断 thinking / reasoning 是否已经结束。

目前本次核对里，官方明确系统列出的重点返回头有：

| 厂商 | 建议保留的返回头 | 作用 |
|---|---|---|
| OpenAI | `x-request-id` | 上游请求追踪 |
| OpenAI | `x-ratelimit-*` | 限流排查 |
| OpenAI | `openai-processing-ms` | 处理耗时观测 |
| OpenAI | `openai-version`、`openai-organization` | 环境与组织侧辅助排错 |
| Claude | `request-id` | 上游请求追踪 |
| Claude | `anthropic-organization-id` | 组织侧辅助排错 |

统一建议：

- 每次上游调用都把自家 `request_id` 和厂商 `request-id` 同时记下来。
- 返回头进入 observability，不进入业务主数据模型。
- 不要因为某家没公开返回头表，就在规范里写经验字段当真值。

---

## 7. easyStory 接入建议

建议把解析契约显式落到 provider runtime：

| 内部语义 | 建议 |
|---|---|
| `response_dialect` | 至少区分 `openai_responses / openai_chat_completions / anthropic_messages / gemini_native` |
| `stream_protocol` | 区分 `semantic_sse / named_sse / openai_chunk_sse / full-response-sse` |
| `text_accumulator` | 区分 `output_text / delta.content / parts[].text` |
| `reasoning_accumulator` | 区分 `reasoning_content / thinking_delta / reasoning_details / none` |
| `usage_policy` | 区分 `final_only / cumulative_deltas / optional_final_chunk` |
| `provider_request_id_header` | 保存真实返回头名，例如 `x-request-id` 或 `request-id` |

实现约束：

1. 参数适配层和响应解析层分开测，不要混成一个 integration blob。
2. 流式解析必须按厂商事件名或 chunk 结构建状态机，不要只做字符串拼接。
3. SSE reader 必须保持长寿命读取，不要因为轮询超时或心跳检查而取消底层流读取任务。
4. `Responses` 一类语义化 SSE 协议要同时维护“渐进文本”和“终态完整响应”两条线；前者服务 UI 增量渲染，后者服务最终文本、`usage` 和完成判定。
5. `reasoning_content` 一律和用户可见 `content` 分轨保存，避免误渲染到终端。
6. 厂商返回头只进日志 / 观测，不要拿它驱动业务分支。

---

## 8. 官方来源

### OpenAI

- [Migrate to the Responses API](https://platform.openai.com/docs/guides/migrate-to-responses)
- [Streaming responses](https://platform.openai.com/docs/guides/streaming-responses?api-mode=responses)
- [Authentication](https://platform.openai.com/docs/api-reference/create-and-export-an-api-key)

### Anthropic

- [API overview](https://docs.anthropic.com/en/api/overview)
- [Streaming Messages](https://docs.anthropic.com/en/api/streaming)

### Google Gemini

- [Text generation](https://ai.google.dev/gemini-api/docs/text-generation)
- [OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai)

### Moonshot Kimi

- [API Reference](https://platform.moonshot.ai/docs/api-reference)
- [Use Kimi K2 Thinking Model](https://platform.moonshot.ai/docs/guide/use-kimi-k2-thinking-model)

### MiniMax

- [文本合成原生接口](https://platform.minimaxi.com/docs/api-reference/text-post)
- [OpenAI API 兼容](https://platform.minimaxi.com/docs/api-reference/text-openai-api)

### Zhipu GLM

- [HTTP API 调用](https://docs.bigmodel.cn/cn/guide/develop/http/introduction)

### DeepSeek

- [Create Chat Completion](https://api-docs.deepseek.com/api/create-chat-completion)
- [DeepSeek API Docs 首页](https://api-docs.deepseek.com/)
