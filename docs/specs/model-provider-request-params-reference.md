# 主流模型厂商请求参数参考

| 字段 | 内容 |
|---|---|
| 文档类型 | 技术规范 / 接口参考 |
| 文档状态 | 生效 |
| 创建时间 | 2026-04-02 |
| 更新时间 | 2026-04-04 |
| 关联文档 | [技术栈确定](./tech-stack.md)、[系统架构设计](./architecture.md)、[数据库设计](./database-design.md)、[主流模型厂商请求头与客户端标识参考](./model-provider-client-identity-and-headers-reference.md)、[主流模型厂商响应结构与流式事件参考](./model-provider-response-contract-reference.md) |

---

## 1. 适用范围

本文整理 `OpenAI GPT / Anthropic Claude / Google Gemini / Moonshot Kimi / MiniMax / Zhipu GLM / DeepSeek` 的官方请求格式、流式输出、思考参数、上下文窗口和最大输出上限，供 easyStory 后端做模型方言适配时参考。

使用原则：

- 只采纳官方文档和官方模型页。
- “标准格式”优先写厂商当前推荐主协议，不优先写兼容层。
- token 上限始终以对应模型页为准；同厂商不同模型可能不同。
- 对官方未明确公布的硬上限，本文会明确标注“官方未单列”。
- 当前 easyStory runtime 原生只实现 `openai_chat_completions / openai_responses / anthropic_messages / gemini_generate_content` 四类方言；`Kimi / MiniMax / GLM / DeepSeek` 当前仍主要按 OpenAI-compatible 家族接入，不等于仓库里已经实现各自 vendor-native dialect。

口径校准：

- OpenAI 模型页中的定价分段或超长上下文计费阈值，不等于模型能力上限；例如 `gpt-5.4` 的 `272K` 是额外计费阈值，不是上下文窗口上限。
- Gemini 3 的模型名与 `thinkingLevel` 取值，以当前官方模型目录和 thinking 文档为准；不要把旧 preview 代理、OpenAI 兼容层或第三方文章里的限制直接当成官方 REST 真值。

---

## 2. 一页总览

| 厂商 | 当前推荐协议 | 是否支持 `v1/chat/completions` 思路 | 主要请求体根字段 | 思考参数 | 流式开关 | 主流模型上下文 / 最大输出 | 最容易踩坑的差异 |
|---|---|---|---|---|---|---|---|
| OpenAI | `POST /v1/responses` | 支持，且仍受支持 | `input` / `instructions` | `reasoning.effort` | `stream: true` | `gpt-5.4` 为 `1,050,000 / 128K` | 新项目推荐 Responses；响应结构是 `output[]`，不是 `choices[]` |
| Claude | `POST /v1/messages` | 原生不支持 | `messages` + 顶层 `system` | `thinking` | `stream: true` | `claude-opus-4-6` 为 `1M / 128K` | `system` 不能写成 `messages[].role=system` |
| Gemini | `models/*:generateContent` | 支持，通过 OpenAI 兼容层 | `contents` + `system_instruction` + `generationConfig` | `thinkingLevel` 或 `thinkingBudget` | `streamGenerateContent?alt=sse` | `gemini-3-pro-preview` 为 `1,048,576 / 65,536` | Gemini 3 和 2.5 的 thinking 参数不是一套 |
| Kimi | `POST /v1/chat/completions` | 原生就是该格式 | `messages` | `thinking.type` 或专用 thinking 模型 | `stream: true` | `kimi-k2.5` 系列 `256K / 官方未单列` | K2.5 很多采样参数是固定值，乱传会报错 |
| MiniMax | 原生 `POST /v1/text/chatcompletion_v2` | 支持，通过 OpenAI 兼容层 | `messages` | 原生接口无 OpenAI 风格 thinking 参数；兼容层可分离 reasoning | `stream: true` | M2 系列 `204,800 / 官方未统一公布硬上限` | 兼容 OpenAI / Anthropic，但能力和字段并不完全等价 |
| GLM | `POST /api/paas/v4/chat/completions` | 请求体兼容，但路径不是 `/v1` | `messages` | `thinking.type` | `stream: true` | `glm-5` 为 `200K / 128K` | `tool_stream` 是智谱特有开关 |
| DeepSeek | `POST /chat/completions` | 请求体兼容，但路径不是 `/v1` | `messages` | `thinking.type` 或 `deepseek-reasoner` | `stream: true` | `deepseek-chat` 为 `128K / 8K`，`deepseek-reasoner` 为 `128K / 64K` | thinking 模式下很多 OpenAI 采样参数会失效或报错 |

---

## 3. 广泛兼容格式：`v1/chat/completions`

虽然各厂商当前“主协议”并不统一，但工程上最常见的兼容层仍然是 `POST /v1/chat/completions` 或其近似变体。很多代理、SDK、模型网关、凭证中心和第三方平台，默认都先假设这一套结构。

最常见的兼容请求体长这样：

```json
{
  "model": "some-model",
  "messages": [
    { "role": "system", "content": "You are a helpful assistant." },
    { "role": "user", "content": "Hello" }
  ],
  "max_tokens": 4096,
  "temperature": 0.7,
  "tools": [],
  "tool_choice": "auto",
  "response_format": { "type": "json_object" },
  "stream": true,
  "stream_options": { "include_usage": true }
}
```

这套兼容格式里最稳定的公共字段是：

- `model`
- `messages`
- `stream`
- `tools`
- `tool_choice`
- `response_format`

最不稳定、最容易出错的字段是：

- `max_tokens`：有的厂商改叫 `max_completion_tokens` 或 `max_output_tokens`
- `system`：有的放顶层，有的放 `messages`
- `thinking/reasoning`：字段名、可选值、是否支持、是否能和采样参数共存，全都不统一
- `stream`：开关相似，但返回 chunk 结构和事件语义不统一

兼容情况一览：

| 厂商 | 兼容情况 | 兼容入口 | 备注 |
|---|---|---|---|
| OpenAI | 原生支持 | `/v1/chat/completions` | 但官方对新项目更推荐 Responses API |
| Gemini | 官方兼容支持 | `/v1beta/openai/chat/completions` | Google 明确说若不是为了兼容 OpenAI SDK，仍更推荐直接调用 Gemini API |
| Kimi | 原生支持 | `/v1/chat/completions` | 主路径就是 OpenAI-compatible Chat Completions |
| MiniMax | 官方兼容支持 | `OPENAI_BASE_URL=https://api.minimaxi.com/v1` | 和原生 `/v1/text/chatcompletion_v2` 不是完全等价 |
| GLM | 结构高度兼容 | `/api/paas/v4/chat/completions` | 路径不是 `/v1`，但请求体接近 |
| DeepSeek | 结构高度兼容 | `/chat/completions` | 路径不是 `/v1`，但请求体接近 |
| Claude | 不走这套 | `/v1/messages` | 原生是 Messages API，不是 Chat Completions |

兼容层接入时必须额外注意：

- Gemini 虽兼容 OpenAI SDK，但 `reasoning_effort` 与 Gemini 原生 `thinkingLevel/thinkingBudget` 不是一一等价透传。
- DeepSeek 看起来最像 OpenAI Chat Completions，但 thinking 模式下很多 OpenAI 采样参数会失效或报错。
- Kimi K2.5 虽然走 Chat Completions 外壳，但多个采样参数是固定值，不是任意可配。
- MiniMax OpenAI 兼容层会忽略部分 OpenAI 参数，不能假设“传了就生效”。
- GLM / DeepSeek 虽然不是严格 `/v1/chat/completions` 路径，但在 runtime 方言层通常仍应归入 `openai_chat_completions` 家族处理。

---

## 4. 跨厂商字段映射

| 语义概念 | OpenAI | Claude | Gemini | Kimi | MiniMax | GLM | DeepSeek |
|---|---|---|---|---|---|---|---|
| 系统提示词 | `instructions` 或 `input` 中 `system/developer` | 顶层 `system` | `system_instruction`（REST）/ `systemInstruction`（SDK） | `messages[].role=system` | `messages[].role=system` | `messages[].role=system` | `messages[].role=system` |
| 多轮输入 | `input` | `messages` | `contents` | `messages` | `messages` | `messages` | `messages` |
| 最大输出 | `max_output_tokens` | `max_tokens` | `generationConfig.maxOutputTokens` | `max_completion_tokens` | `max_completion_tokens` | `max_tokens` | `max_tokens` |
| 流式输出 | `stream: true` | `stream: true` | `:streamGenerateContent?alt=sse` | `stream: true` | `stream: true` | `stream: true` | `stream: true` |
| 思考控制 | `reasoning` | `thinking` | `thinkingConfig` | `thinking` | 兼容层 / 模型行为 | `thinking` | `thinking` / `deepseek-reasoner` |
| 工具调用 | `tools` / `tool_choice` | `tools` / `tool_choice` | function calling | `tools` / `tool_choice` | `tools` / `tool_choice` | `tools` / `tool_stream` | `tools` / `tool_choice` |
| 结构化输出 | `text.format` 或 JSON 输出 | tools / 内容块 / JSON 自行约束 | `responseMimeType` + structured outputs | `response_format` | `response_format` | 结构化输出能力 | `response_format` |

统一接入结论：

- 不要把“思考参数”抽象成一个裸 `reasoning_effort` 后强行塞给所有厂商。
- 至少要区分 `openai_responses / anthropic_messages / gemini_generate_content / openai_chat_compat` 四类方言。
- `max output` 也不能统一写成一个字段名直接透传。
- 当前 easyStory runtime 真正已经落地的原生请求 builder 也只有这四类；其余厂商的接入文档是参考真值，不代表运行时代码已拥有 vendor-native 参数适配。

---

## 5. OpenAI GPT

**标准格式（推荐）**：`POST https://api.openai.com/v1/responses`

**兼容入口（仍受支持）**：`POST https://api.openai.com/v1/chat/completions`

```json
{
  "model": "gpt-5.4",
  "input": [{"role": "user", "content": "..." }],
  "reasoning": { "effort": "low" },
  "max_output_tokens": 8192,
  "stream": true
}
```

核心参数：

| 参数 | 作用 | 备注 |
|---|---|---|
| `model` | 指定模型 | 推荐直接用最新稳定模型名 |
| `input` | 输入消息或多模态内容 | 最新主字段，不是 `messages` |
| `instructions` | 顶层系统约束 | 可替代部分 system message 用法 |
| `max_output_tokens` | 限制输出 token | 包含 reasoning token + 可见输出 |
| `reasoning.effort` | 控制思考深度 | 支持值按模型而变 |
| `reasoning.summary` | 返回思考摘要 | 不是返回原始 CoT |
| `stream` | SSE 流式 | 常见事件有 `response.created`、`response.output_text.delta`、`response.completed` |
| `text.format` / `text.verbosity` | 控制文本输出格式与详略 | 仅部分模型或场景可用 |
| `tools` / `tool_choice` | 工具调用 | Responses API 原生支持 |

主流模型上限：

| 模型 | 上下文窗口 | 最大输出 |
|---|---|---|
| `gpt-5.4` | 1,050,000 | 128K |
| `gpt-5.4-mini` | 400K | 128K |
| `gpt-5.4-nano` | 400K | 128K |

注意事项：

- OpenAI 官方当前明确推荐新项目优先使用 Responses API，但 Chat Completions 仍受支持，并且可以渐进迁移。
- 如果要做 reasoning / agentic / Codex-like runtime，优先实现 `openai_responses` 方言，不要只做 `chat/completions`。
- `gpt-5.4` 官方模型页给出的上下文窗口是 `1,050,000`；其中超过 `272K` 输入 token 的会话会有额外定价规则，不要把它写成“只有特定配置才支持 1M”。
- `max_output_tokens` 太小会直接把预算耗在 reasoning 上，最后返回 `status=incomplete`。
- 官方建议刚开始给 reasoning 模型预留足够预算；文档示例建议先按至少 `25,000` token 量级试验。
- 响应解析不要沿用 `choices[]` 老逻辑；`Responses` 与 `Chat Completions` 的响应结构和 SSE 结束信号不同，见 [主流模型厂商响应结构与流式事件参考](./model-provider-response-contract-reference.md)。
- `stream: true` 只表示切到 SSE；工程实现上应把“读流稳定性”和“事件协议解析”分开处理，不要用短超时去取消底层流 reader。
- `Responses` 流式的最终文本与 `usage` 应优先从 `response.completed` / 最终 `response` 对象收束，而不是假设一定先收到 `response.output_text.delta`。

---

## 6. Anthropic Claude

**标准格式**：`POST https://api.anthropic.com/v1/messages`

```json
{
  "model": "claude-sonnet-4-6",
  "system": "You are ...",
  "messages": [{ "role": "user", "content": "..." }],
  "max_tokens": 4096,
  "stream": true
}
```

核心参数：

| 参数 | 作用 | 备注 |
|---|---|---|
| `model` | 指定模型 | 以模型页 alias 为准 |
| `system` | 系统提示词 | 顶层字段，不在 `messages` 里写 `system` role |
| `messages` | 多轮上下文 | 用户和助手轮次交替 |
| `max_tokens` | 最大输出 | Claude 用这个名字 |
| `temperature` / `top_p` / `top_k` | 采样控制 | 与 thinking 有兼容限制 |
| `stop_sequences` | 停止词 | 多个字符串 |
| `thinking` | 扩展思考 | 4.6 系列更推荐 adaptive thinking |
| `tools` / `tool_choice` | 工具调用 | 原生支持 |
| `stream` | SSE 流式 | 事件主流程是 `message_start -> content_block_* -> message_delta -> message_stop` |

主流模型上限：

| 模型 | 上下文窗口 | 最大输出 |
|---|---|---|
| `claude-opus-4-6` | 1M | 128K |
| `claude-sonnet-4-6` | 1M | 64K |
| `claude-haiku-4-5` | 200K | 64K |

注意事项：

- `thinking` 开启后，官方明确说它和修改 `temperature`、`top_k`、强制 tool use 不兼容。
- 开启 thinking 时，`top_p` 只能在 `0.95` 到 `1` 之间。
- 手动 budget 模式下，`budget_tokens` 最小 `1024`，且通常必须小于 `max_tokens`。
- 改 thinking budget 会让带 message 的 prompt cache 失效。

---

## 7. Google Gemini

**标准格式**：`POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`

```json
{
  "contents": [{ "parts": [{ "text": "..." }] }],
  "generationConfig": {
    "maxOutputTokens": 8192,
    "thinkingConfig": { "thinkingLevel": "low" }
  }
}
```

流式接口：`...:streamGenerateContent?alt=sse`

核心参数：

| 参数 | 作用 | 备注 |
|---|---|---|
| `contents` | 输入内容 | 主字段，不叫 `messages` |
| `system_instruction` | 系统提示词 | REST 原生字段；SDK 常封装成 `systemInstruction` |
| `generationConfig.maxOutputTokens` | 最大输出 | Gemini 命名 |
| `temperature` / `topP` / `topK` | 采样参数 | Gemini 3 官方建议温度保持默认 `1.0` |
| `stopSequences` | 停止词 | 放在 `generationConfig` |
| `responseMimeType` | 输出 MIME | 如 `application/json` |
| `thinkingConfig.thinkingLevel` | Gemini 3 思考强度 | 官方当前文档：`Gemini 3 Pro` 支持 `low/medium/high`；`Gemini 3 Flash` 支持 `minimal/low/medium/high` |
| `thinkingConfig.thinkingBudget` | Gemini 2.5 思考预算 | `0` 关闭，`-1` 动态 |

主流模型上限：

| 模型 | 上下文窗口 | 最大输出 |
|---|---|---|
| `gemini-2.5-pro` | 1,048,576 | 65,536 |
| `gemini-2.5-flash` | 1,048,576 | 65,536 |
| `gemini-3-pro-preview` | 1,048,576 | 65,536 |
| `gemini-3-flash-preview` | 1,048,576 | 65,536 |

注意事项：

- Gemini 3 推荐 `thinkingLevel`，Gemini 2.5 推荐 `thinkingBudget`；两套参数不要混用。
- 官方当前 thinking 文档里，`Gemini 3 Pro` 已列出 `low/medium/high`；但部分旧 preview 代理或 OpenAI 兼容层对 Pro 的 `medium` 仍可能不稳定，工程上应把“官方 REST 能力”和“代理兼容性”分开记录。
- `gemini-3-pro-preview` 不能关闭 thinking；不指定时会使用默认动态高思考。
- `gemini-3-flash-preview` 的 `minimal` 不等于绝对关闭 thinking。
- `gemini-2.5-pro` 也不能关闭 thinking；`gemini-2.5-flash` 可通过 `thinkingBudget=0` 关闭。
- 如果需要保留工具调用中的 thought context，Gemini 会返回 thought signatures；REST 直连时应原样传回。
- SDK 里的 chat 只是便利封装，底层仍是 `generateContent`，每轮会重发完整历史。

---

## 8. Moonshot Kimi

**标准格式**：`POST https://api.moonshot.ai/v1/chat/completions`

```json
{
  "model": "kimi-k2.5",
  "messages": [{ "role": "user", "content": "..." }],
  "max_completion_tokens": 8192,
  "stream": true
}
```

核心参数：

| 参数 | 作用 | 备注 |
|---|---|---|
| `model` | 指定模型 | K2.5、K2-thinking、moonshot-v1-* 等 |
| `messages` | 多轮上下文 | OpenAI 兼容结构 |
| `max_completion_tokens` | 最大输出 | 官方建议用它，不再优先用 `max_tokens` |
| `temperature` / `top_p` / `n` / penalties | 采样控制 | `kimi-k2.5` 对这些值有限定 |
| `response_format` | JSON 输出 | `json_object` |
| `thinking` | 开关 thinking | 仅 `kimi-k2.5` 有 `enabled/disabled` |
| `stream` | 流式输出 | SSE chunk，`reasoning_content` 先于 `content` |
| `stream_options.include_usage` | 末块 usage | 兼容 OpenAI 习惯 |
| `prompt_cache_key` | 提高缓存命中 | agent / 会话场景建议带上 |
| `tools` / `tool_choice` | 工具调用 | K2.5 thinking 模式有限制 |

主流模型上限：

| 模型 | 上下文窗口 | 最大输出 |
|---|---|---|
| `kimi-k2.5` | 256K | 官方未单列硬上限 |
| `kimi-k2-thinking` | 256K | 官方未单列硬上限 |
| `moonshot-v1-8k/32k/128k` | 8K / 32K / 128K | 输出上限约等于上下文减去输入 |

注意事项：

- `kimi-k2.5` 的 `temperature/top_p/n/presence_penalty/frequency_penalty` 基本是固定值，传别的值会报错。
- `kimi-k2.5` thinking 开启时，`tool_choice` 只能是 `auto` 或 `none`。
- thinking + tool call 的多步过程中，必须保留 `reasoning_content`；否则会报错。
- 官方明确说 builtin `$web_search` 暂时不兼容 K2.5 thinking 模式。

---

## 9. MiniMax

**原生标准格式**：`POST https://api.minimaxi.com/v1/text/chatcompletion_v2`

```json
{
  "model": "MiniMax-M2.7",
  "messages": [{ "role": "user", "content": "..." }],
  "max_completion_tokens": 8192,
  "stream": true
}
```

核心参数：

| 参数 | 作用 | 备注 |
|---|---|---|
| `model` | 指定模型 | 当前主流是 M2.* 系列 |
| `messages` | 多轮上下文 | 原生接口字段 |
| `stream` | 流式输出 | `text/event-stream` |
| `max_completion_tokens` | 最大输出 | `max_tokens` 已废弃 |
| `temperature` / `top_p` | 采样控制 | M2 推荐 `1.0 / 0.95` |
| `tools` / `tool_choice` | 工具调用 | 原生支持 |
| `response_format` | 结构化输出 | 原生文档注明目前仅部分模型支持 |
| `stream_options.include_usage` | 末块 usage | 原生支持 |

主流模型上限：

| 模型 | 上下文窗口 | 最大输出 |
|---|---|---|
| `MiniMax-M2.7` | 204,800 | 官方未统一公布硬上限 |
| `MiniMax-M2.5` | 204,800 | 官方未统一公布硬上限 |
| `MiniMax-M2.1` | 204,800 | 官方未统一公布硬上限 |
| `MiniMax-M2` | 204,800 | 官方文档明确默认 `max_completion_tokens=10240` |

注意事项：

- MiniMax 同时提供原生接口、OpenAI 兼容接口、Anthropic 兼容接口，三者不应视为完全等价。
- OpenAI 兼容层可通过 `extra_body.reasoning_split=true` 把思考内容拆到 `reasoning_details`。
- OpenAI 兼容层会忽略部分 OpenAI 参数，如 `presence_penalty`、`frequency_penalty`、`logit_bias`。
- OpenAI 兼容层当前 `n` 只支持 `1`。
- 多轮 function call 必须保留完整 assistant message，不要只留 `content`。

---

## 10. Zhipu GLM

**标准格式**：`POST https://open.bigmodel.cn/api/paas/v4/chat/completions`

```json
{
  "model": "glm-5",
  "messages": [{ "role": "user", "content": "..." }],
  "thinking": { "type": "enabled" },
  "stream": true,
  "max_tokens": 8192
}
```

核心参数：

| 参数 | 作用 | 备注 |
|---|---|---|
| `model` | 指定模型 | 当前旗舰为 `glm-5` |
| `messages` | 多轮上下文 | OpenAI 风格结构 |
| `thinking.type` | 思考模式 | `enabled/disabled` |
| `stream` | 流式输出 | SSE，`delta.reasoning_content` 和 `delta.content` 分开给出 |
| `max_tokens` | 最大输出 | 智谱命名 |
| `temperature` / `top_p` | 采样参数 | 官方迁移文档建议一般不要同时调两者 |
| `tools` | 工具列表 | 原生支持 |
| `tool_stream` | 流式工具参数 | 仅在工具调用流式场景下有意义，且需配合 `stream=true` |

主流模型上限：

| 模型 | 上下文窗口 | 最大输出 |
|---|---|---|
| `glm-5` | 200K | 128K |
| `glm-5-turbo` | 200K | 128K |
| `glm-4.7` | 200K | 128K |
| `glm-4.6` | 200K | 128K |

注意事项：

- 智谱最新旗舰是 `GLM-5`，但 `GLM-4.6/4.7` 仍是常见稳定接入对象。
- 深度思考开启后会返回 `reasoning_content`，流式和非流式都一样要按字段接。
- `tool_stream=true` 是智谱特有能力，不属于 OpenAI 通用字段。

---

## 11. DeepSeek

**标准格式**：`POST https://api.deepseek.com/chat/completions`

```json
{
  "model": "deepseek-chat",
  "messages": [{ "role": "user", "content": "..." }],
  "thinking": { "type": "enabled" },
  "max_tokens": 8192,
  "stream": true
}
```

核心参数：

| 参数 | 作用 | 备注 |
|---|---|---|
| `model` | `deepseek-chat` 或 `deepseek-reasoner` | 两者共享 Chat Completions 结构 |
| `messages` | 多轮上下文 | OpenAI 风格结构 |
| `thinking.type` | 开关 thinking | 也可直接切到 `deepseek-reasoner` |
| `max_tokens` | 最大输出 | 包含 reasoning + final answer |
| `response_format` | JSON 输出 | `json_object` |
| `stream` | SSE 流式 | `data: [DONE]` 结束 |
| `stream_options.include_usage` | usage 末块 | thinking 模式也适用 |
| `tools` / `tool_choice` | 工具调用 | thinking 模式已支持工具调用 |

主流模型上限：

| 模型 | 上下文窗口 | 默认最大输出 | 硬最大输出 |
|---|---|---|---|
| `deepseek-chat` | 128K | 4K | 8K |
| `deepseek-reasoner` | 128K | 32K | 64K |

注意事项：

- thinking 模式下，`temperature/top_p/presence_penalty/frequency_penalty` 不会生效。
- thinking 模式下，`logprobs/top_logprobs` 会直接报错。
- 普通新一轮对话时，不要把上一轮 `reasoning_content` 继续塞回去。
- 但在“同一轮问题内部的多次 tool call 子回合”里，又必须把 `reasoning_content` 带回去，否则会 `400`。
- 这正是最典型的“OpenAI 兼容表面一致、thinking 语义实际不一致”的来源。

---

## 12. easyStory 接入建议

建议在运行时保留以下内部抽象，而不是直接做一套“所有厂商都通用”的裸透传：

| 内部语义 | 建议 |
|---|---|
| `api_dialect` | 至少区分 `openai_responses / anthropic_messages / gemini_generate_content / openai_chat_completions` |
| `thinking_mode` | 不要只保留一个 effort 字段；应支持 `none / adaptive / level / budget / enabled-disabled` 几类语义 |
| `context_window_tokens` | 记录到连接或模型元数据，不要伪装成统一请求参数 |
| `default_max_output_tokens` | 记录到连接级默认值；真正发请求时再映射到各家字段名 |
| `tool_call_history_policy` | 对 Kimi / MiniMax / DeepSeek / Claude 分别处理 reasoning / tool blocks 回传规则 |

最重要的工程约束：

1. OpenAI 的最新主协议和 OpenAI-compatible Chat Completions 不是一回事。
2. thinking / reasoning 绝不能只按字段名兼容，必须按语义兼容。
3. stream 的“开关”看起来接近，但返回事件格式并不统一，解析器必须按厂商分支。

---

## 13. 官方来源

### OpenAI

- [Migrate to the Responses API](https://platform.openai.com/docs/guides/migrate-to-responses)
- [GPT-5.4](https://developers.openai.com/api/docs/models/gpt-5.4)
- [GPT-5.4 mini](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
- [Responses API](https://platform.openai.com/docs/api-reference/responses/create)
- [Chat Completions API](https://platform.openai.com/docs/api-reference/chat)
- [Streaming Responses](https://platform.openai.com/docs/guides/streaming-responses?api-mode=responses)
- [Reasoning Models](https://platform.openai.com/docs/guides/reasoning?api-mode=responses)
- [Models](https://platform.openai.com/docs/models)
- [Chat Completions Guide](https://platform.openai.com/docs/guides/chat-completions)

### Anthropic

- [Messages API](https://docs.anthropic.com/en/api/messages)
- [Streaming Messages](https://docs.anthropic.com/en/api/streaming)
- [Extended Thinking](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking)
- [Models Overview](https://docs.anthropic.com/en/docs/about-claude/models/overview)

### Google Gemini

- [Text Generation](https://ai.google.dev/gemini-api/docs/text-generation)
- [Thinking](https://ai.google.dev/gemini-api/docs/thinking)
- [Models Overview](https://ai.google.dev/gemini-api/docs/models)
- [OpenAI Compatibility](https://ai.google.dev/gemini-api/docs/openai)
- [Gemini Models Catalog](https://ai.google.dev/models/gemini)
- [Gemini 2.5 Pro](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-pro)
- [Gemini 2.5 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash)
- [Gemini 3 Flash Preview](https://ai.google.dev/gemini-api/docs/models/gemini-3-flash-preview)

### Moonshot Kimi

- [API Reference](https://platform.moonshot.ai/docs/api-reference)
- [Kimi K2.5](https://platform.moonshot.ai/docs/guide/kimi-k2-5-quickstart)
- [Use Kimi K2 Thinking Model](https://platform.moonshot.ai/docs/guide/use-kimi-k2-thinking-model)
- [Streaming Output Guide](https://platform.moonshot.ai/docs/guide/utilize-the-streaming-output-feature-of-kimi-api)

### MiniMax

- [文本合成原生接口](https://platform.minimaxi.com/docs/api-reference/text-post)
- [OpenAI API 兼容](https://platform.minimaxi.com/docs/api-reference/text-openai-api)
- [文本生成总览](https://platform.minimaxi.com/docs/guides/text-generation)

### Zhipu GLM

- [模型概览](https://docs.bigmodel.cn/cn/guide/start/model-overview)
- [GLM-5](https://docs.bigmodel.cn/cn/guide/models/text/glm-5)
- [流式消息](https://docs.bigmodel.cn/cn/guide/capabilities/streaming)
- [深度思考](https://docs.bigmodel.cn/cn/guide/capabilities/thinking)

### DeepSeek

- [Create Chat Completion](https://api-docs.deepseek.com/api/create-chat-completion)
- [Reasoning Model](https://api-docs.deepseek.com/guides/reasoning_model)
- [Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode)
- [Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing)
