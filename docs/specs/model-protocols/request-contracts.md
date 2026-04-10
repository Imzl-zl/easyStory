# 请求契约

| 字段 | 内容 |
|---|---|
| 文档类型 | 技术规范 / 请求契约 |
| 文档状态 | 生效 |
| 创建时间 | 2026-04-10 |
| 更新时间 | 2026-04-10 |
| 关联文档 | [支持范围与治理规则](./supported-dialects-and-governance.md)、[响应、流式与终态装配](./response-streaming-and-terminal-assembly.md) |

---

## 1. 可移植的 canonical request

一个跨协议 agent runtime，建议先把内部请求抽象成这几组字段：

- `model`
- `instructions`
  - 系统指令 / developer instruction
- `conversation_items`
  - 用户消息、历史助手消息、上一轮 tool result 等
- `generation_controls`
  - `max_output_tokens / temperature / top_p / stop`
- `reasoning_controls`
  - reasoning / thinking 深度相关控制
- `tool_declarations`
  - 自定义函数工具的定义
- `continuation_context`
  - provider continuation state 或 runtime replay 所需上下文
- `response_format_controls`
  - 纯文本、JSON mode、结构化输出 schema
- `transport_preferences`
  - 是否流式、是否允许并行工具等

## 2. 4 个协议族的请求映射

| 协议族 | endpoint | 主输入字段 | 系统指令字段 | 输出上限字段 | 工具定义字段 | 结构化输出字段 |
|---|---|---|---|---|---|---|
| `openai_responses` | `POST /v1/responses` | `input` | `instructions` | `max_output_tokens` | `tools[]` | `text.format` |
| `openai_chat_completions` | `POST /v1/chat/completions` | `messages` | `messages[].role=system/developer` | 官方推荐 `max_completion_tokens`，兼容网关常见 `max_tokens` | `tools[].function` | `response_format` |
| `anthropic_messages` | `POST /v1/messages` | `messages` | 顶层 `system` | `max_tokens` | `tools[].input_schema` | 无统一 JSON mode 字段 |
| `gemini_generate_content` | `POST /v1beta/models/{model}:generateContent` | `contents` | `systemInstruction` | `generationConfig.maxOutputTokens` | `tools[].functionDeclarations[]` | `generationConfig.responseMimeType` + 可选 `responseJsonSchema` |

## 3. OpenAI Responses

官方事实：

- 使用 `input` 而不是 `messages`
- 系统级指令通过 `instructions`
- 推理控制通过 `reasoning`
- 工具通过 `tools[]`
- 输出上限通过 `max_output_tokens`
- 多轮续接可使用 `previous_response_id`

可移植建议：

- 即使使用 provider continuation，也保留自己的一份 canonical continuation items
- 把 JSON mode、structured output 和 tool calling 作为三个独立能力面建模

## 4. OpenAI Chat Completions

官方事实：

- 输入主字段是 `messages`
- 仍支持工具调用
- `tool_choice` 支持 `none / auto / required` 以及指定具体函数
- `max_tokens` 已被标为 deprecated，官方更推荐 `max_completion_tokens`

可移植建议：

- 对官方 OpenAI 直连优先用 `max_completion_tokens`
- 对兼容网关保留 `max_tokens` 兼容层
- 对 reasoning 参数按模型能力判断，不要把单一参数硬塞进所有 chat-compatible 渠道

## 5. Anthropic Messages

官方事实：

- 顶层必须有 `max_tokens`
- `system` 不在 `messages` 内
- 所有请求必须带 `x-api-key` 和 `anthropic-version`
- 工具通过 `tools[]` 声明，参数字段是 `input_schema`
- `tool_choice` 支持 `auto / any / tool / none`
- `disable_parallel_tool_use` 是官方字段

可移植建议：

- 如果你的本地 tool loop 一次只想处理一个工具调用，可以显式关闭并行 tool use
- 不要把 Anthropic 的工具消息格式硬塞回 OpenAI 风格 replay

## 6. Gemini GenerateContent

官方事实：

- endpoint 是 `models/*:generateContent`
- 输入主字段是 `contents`
- 系统指令字段是 `systemInstruction`
- 工具通过 `tools[].functionDeclarations[]`
- 工具配置通过 `toolConfig.functionCallingConfig`
- JSON mode 通过 `generationConfig.responseMimeType=\"application/json\"`
- 结构化输出可进一步提供 `responseJsonSchema`

实践坑位：

- Google 官方参考常用 camelCase 字段名，例如 `systemInstruction / toolConfig / generationConfig`
- 部分 REST 示例会出现 snake_case 片段
- 如果做跨项目 runtime，建议内部统一一种编码风格，并在 codec 层处理，不要在业务层混用

## 7. 工具声明的可移植最小交集

跨 OpenAI / Anthropic / Gemini 时，最稳妥的自定义函数工具声明建议是：

- 根 schema 用 `object`
- 参数类型只用常见 JSON Schema / OpenAPI 基本类型
- 明确 `required`
- 描述清晰，不依赖复杂组合 schema
- 工具名使用安全 ASCII

Gemini 官方文档明确建议活动工具集尽量保持在相关且有限的范围内，理想情况下控制在大约 `10-20` 个以内。

## 8. 结构化输出与工具调用要分开

这是跨项目最容易踩坑的一点：

- `structured output`
  - 目标是约束最终回答格式
- `function calling`
  - 目标是让模型决定是否调用工具

二者都使用 schema，但不是同一个能力面。

实践建议：

- 当你要“调用外部能力”时，优先用 function calling
- 当你要“约束最终回答格式”时，优先用 structured output / JSON mode
- 不要把“让模型回 JSON”误当成“已经具备稳定 tool-calling”

## 9. 流式请求开关

可移植 runtime 通常需要单独处理流式 transport：

- OpenAI / Anthropic 一般通过 body 的 `stream=true`
- Gemini 原生通常需要切换到 `streamGenerateContent`
- 所有协议都应显式设置 `Accept: text/event-stream`

## 10. 一句话边界

请求标准文档只回答“不同协议该怎么发”。  
某个项目内部把这些字段命名成什么、如何持久化、默认值是多少，应该放到 adoption profile。
