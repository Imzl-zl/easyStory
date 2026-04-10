# 响应、流式与终态装配

| 字段 | 内容 |
|---|---|
| 文档类型 | 技术规范 / 响应契约 |
| 文档状态 | 生效 |
| 创建时间 | 2026-04-10 |
| 更新时间 | 2026-04-10 |
| 关联文档 | [请求契约](./request-contracts.md)、[工具调用、续接与一致性验证](./tool-calling-continuation-and-conformance.md) |

---

## 1. 可移植的 canonical response

建议所有协议最终都归一化成一份稳定响应对象，至少包含：

- `content`
- `finish_reason`
- `usage`
  - `input_tokens / output_tokens / total_tokens`
- `tool_calls`
- `provider_response_id`
- `provider_payload_summary`

工具调用本身也建议单独归一化为：

- `tool_call_id`
- `tool_name`
- `arguments`
- `arguments_text`
- `arguments_error`
- `provider_ref`
- `provider_payload`

## 2. 非流式响应主提取位

| 协议族 | 文本提取 | 工具调用提取 | usage 位置 |
|---|---|---|---|
| `openai_responses` | `output_text` 或 `output[].content[].text` | `output[].function_call` | `usage` |
| `openai_chat_completions` | `choices[0].message.content` | `choices[0].message.tool_calls[]` | `usage` |
| `anthropic_messages` | `content[]` 中的 text blocks | `content[]` 中的 `tool_use` blocks | `usage` |
| `gemini_generate_content` | `candidates[0].content.parts[].text` | `parts[].functionCall` | `usageMetadata` |

## 3. 流式 transport 差异

| 协议族 | 流式形态 | 常见增量位置 | 终态信号 |
|---|---|---|---|
| `openai_responses` | 语义化 SSE 事件 | `response.output_text.delta` | `response.completed` |
| `openai_chat_completions` | OpenAI chunk SSE | `choices[0].delta.*` | final chunk + `[DONE]` |
| `anthropic_messages` | 具名 SSE 事件序列 | `content_block_delta` | `message_stop` |
| `gemini_generate_content` | SSE，每条 `data:` 是 `GenerateContentResponse` 片段 | `candidates[].content.parts[]` | 流自然结束，终态信息在最后若干 payload 中 |

## 4. 流式 reader 与协议状态机必须分离

这是做 agent runtime 时的核心原则：

- `stream transport`
  - 负责把 SSE / chunk 完整读出来
- `protocol state machine`
  - 负责解析 text delta、tool delta、usage、stop reason、terminal payload

不要因为 transport 层读超时，就直接推断协议层“无文本 / 无工具调用 / 已完成”。

## 5. Gemini 的终态装配要更保守

Gemini 官方函数调用文档明确提醒：

- 不要假设 `functionCall` 一定是 `parts[]` 的最后一个元素
- 与内置工具混用时，`parts[]` 里可能同时出现 `functionCall / toolCall / toolResponse`
- 解析时应遍历 `parts`，而不是靠位置假设

基于这一点，一个可移植 runtime 在 Gemini 流式下应采用更保守的终态装配策略：

1. 保留整个流中出现过的所有 `functionCall` parts
2. 不要只看最后一个 payload
3. 在最终归一化前，对同一调用做去重
4. 再统一投影成 canonical tool calls

## 6. 常见 stop / finish reason 解释

至少应显式区分：

- 自然完成
- 触发 tool call
- 输出被长度上限截断
- 内容安全 / policy 中断
- 协议错误或无效终态

实践建议：

- `length / max_tokens / max_output_tokens / MAX_TOKENS` 这类终态不要当成功
- “最后没文本”不等于“请求失败”，先看是否有合法 tool call
- “没有 tool call 也没有文本”才是非法空响应

## 7. 每个协议最容易踩坑的点

### 7.1 OpenAI Responses

- 不能按 `choices[]` 旧结构解析
- 流式完成真值看 `response.completed`，不是 `[DONE]`
- 工具调用和文本都可能存在于 `output[]`

### 7.2 OpenAI Chat Completions

- tool call 参数可能在 `delta.tool_calls[]` 中分块到达
- `max_tokens` 截断和 `tool_calls` 终止要区分
- 兼容网关的 usage / final chunk 行为可能与官方略有差异

### 7.3 Anthropic Messages

- 流式是具名事件序列，不是简单 chunk 文本
- `tool_use` / `tool_result` 都是 content blocks
- `input_json_delta` 需要累计后再做 JSON 解析

### 7.4 Gemini

- `parts[]` 可能只有 `functionCall`，没有文本
- `finishReason=STOP` 不代表一定有可展示文本
- 流式解析时必须按 `parts` 全量遍历，不能按位置猜

## 8. 推荐的流式最小测试集

如果你想把这套文档拿去别的项目做 agent，至少要给每个协议族补这几类测试：

1. 纯文本非流式
2. 纯文本流式
3. tool declaration 被接受
4. 首轮真实返回 tool call
5. tool result 回传后能继续推理
6. 长度截断时能显式失败
7. “空文本但有 tool call” 不被误报为空响应

## 9. 一句话边界

响应标准文档只回答“不同协议怎么解析”。  
某个项目当前用哪份 synthesizer、哪些 stop reason 常量、哪些单元测试名，不属于这里的标准层。
