# 主流模型厂商请求头与客户端标识参考

| 字段 | 内容 |
|---|---|
| 文档类型 | 技术规范 / 扩展参考 |
| 文档状态 | 参考 |
| 创建时间 | 2026-04-02 |
| 更新时间 | 2026-04-10 |
| 关联文档 | [模型协议与工具调用标准](./model-protocols/README.md)、[主流模型厂商请求参数参考](./model-provider-request-params-reference.md)、[主流模型厂商响应结构与流式事件参考](./model-provider-response-contract-reference.md)、[技术栈确定](./tech-stack.md)、[系统架构设计](./architecture.md) |

---

> 当前 easyStory shared runtime 的正式鉴权头、User-Agent、`extra_headers` 优先级与客户端身份维护入口，已迁到 [模型协议与工具调用标准](./model-protocols/README.md)。
>
> 本文继续保留更宽口径的厂商资料与浏览器边界说明，但不再作为当前运行时代码的唯一标准真值。

## 1. 适用范围

本文补充 `OpenAI GPT / Anthropic Claude / Google Gemini / Moonshot Kimi / MiniMax / Zhipu GLM / DeepSeek` 的请求头、鉴权方式、客户端标识、OpenAI-compatible 兼容层和浏览器直连边界，供 easyStory 做扩展调研、请求排错和市场资料沉淀时参考。

使用原则：

- 只采纳官方文档、官方 API 参考和官方示例。
- 明确区分“官方必需头”“兼容层头”“浏览器运行时自带头”。
- 本文不讨论绕过风控、冒充官方产品或伪造平台身份。
- 对 Kimi 这类主要通过 OpenAI SDK 兼容示例展示的场景，若文档未单列原始 HTTP 头名，会明确标注“基于官方兼容示例推断”。
- 若要查看当前代码实际采用的 `auth_strategy / api_key_header_name / user_agent_override / client_name / runtime_kind` 规则，请优先看 [客户端身份、鉴权与请求头](./model-protocols/client-identity-auth-and-headers.md)。

---

## 2. 先看结论

- 没有哪家主流厂商公开提供“把请求变成 Claude Code CLI / Codex CLI / Gemini CLI”的官方参数。
- 你真正能合法控制的，通常只有 `Authorization`、版本头、beta 头、你自己的 `User-Agent`、以及你自己的 trace / request id。
- “看起来像 Python”通常只是因为 SDK 默认 `User-Agent`、HTTP 客户端和运行时不同，不等于协议身份不同。
- 浏览器请求和服务端请求不是一回事。浏览器会额外带 `Origin / Referer / Sec-Fetch-* / sec-ch-ua*` 等上下文信息，这些不是模型厂商参数。
- 标准文本 / 聊天 REST API 默认都应走服务端代理。当前官方短期票据方案里，已明确能直接给浏览器用的主要是 `OpenAI Realtime client secret` 和 `Gemini Live API ephemeral token`。
- 返回头能帮助排错和观测，但不能替代按方言解析响应体和流式事件；见 [主流模型厂商响应结构与流式事件参考](./model-provider-response-contract-reference.md)。

---

## 3. 官方请求头一览

| 厂商 | 主协议 / 入口 | 官方必需头 | 常见可选头 | 说明 |
|---|---|---|---|---|
| OpenAI | `POST /v1/responses`（推荐）或 `/v1/chat/completions`（仍受支持） | `Authorization: Bearer <OPENAI_API_KEY>` | `OpenAI-Organization`、`OpenAI-Project`、`X-Client-Request-Id` | `X-Client-Request-Id` 是 OpenAI 明文支持的自定义请求标识 |
| Claude | `POST /v1/messages` | `x-api-key`、`anthropic-version`、`content-type: application/json` | `anthropic-beta` | `anthropic-version` 是必需头，不是可选 metadata |
| Gemini 原生 | `models/*:generateContent` | `x-goog-api-key`、`Content-Type: application/json` | 无统一厂商级可选头 | 原生 Gemini 不走 Bearer，而是 `x-goog-api-key` |
| Gemini OpenAI 兼容层 | `/v1beta/openai/*` | `Authorization: Bearer <GEMINI_API_KEY>`、`Content-Type: application/json` | 无统一厂商级可选头 | 仅在你确实要兼容 OpenAI SDK / Chat Completions 时使用 |
| Kimi | `POST /v1/chat/completions` | 基于官方 OpenAI SDK 兼容示例，按 `Authorization: Bearer <MOONSHOT_API_KEY>` 处理；原始 HTTP 文档未单列独立头表 | 无统一厂商级可选头 | `prompt_cache_key`、`safety_identifier` 是 body 字段，不是请求头 |
| MiniMax 原生 | `POST /v1/text/chatcompletion_v2` | `Authorization: Bearer <API_KEY>`、`Content-Type: application/json` | 无统一厂商级可选头 | 原生 OpenAPI 明确声明 `bearerAuth` |
| MiniMax OpenAI 兼容层 | `https://api.minimaxi.com/v1` | `Authorization: Bearer <API_KEY>`、`Content-Type: application/json` | 无统一厂商级可选头 | 与原生接口能力不完全等价 |
| GLM | `POST /api/paas/v4/chat/completions` | `Authorization: Bearer <API_KEY 或 JWT>`、`Content-Type: application/json` | 无统一厂商级可选头 | 智谱明确支持 API Key 直传或 JWT 鉴权 |
| DeepSeek | `POST /chat/completions` | `Authorization: Bearer <DEEPSEEK_API_KEY>`、`Content-Type: application/json` | 无统一厂商级可选头 | `/v1` 只是兼容 base_url 别名，不代表新的协议版本 |

请求头层面最容易混淆的点：

- OpenAI / Gemini OpenAI 兼容 / Kimi / MiniMax 兼容 / DeepSeek / GLM 看起来都很像 `Authorization: Bearer`，但请求体和 thinking 语义并不等价。
- Claude 的 `anthropic-version` 是硬要求，不带就不是“旧版兼容”，而是请求不合规。
- Gemini 原生和 Gemini OpenAI 兼容层是两套入口，前者主要看 `x-goog-api-key`，后者主要看 `Authorization: Bearer`。

---

## 4. 为什么有时看起来像 Python / Node / CLI

在绝大多数情况下，服务端看到“这是 Python 发的”“这是 Node 发的”，来自以下几类线索：

- HTTP 客户端或官方 SDK 自动带上的 `User-Agent`
- 默认连接栈差异，例如 `requests`、`httpx`、`fetch`、`okhttp`
- 官方 SDK 的请求组织方式，例如默认超时、重试、stream 读取方式
- 某些平台日志中的接入路径或兼容层入口，例如 `/v1/responses`、`/v1/messages`、`/v1beta/openai/chat/completions`

这不等于存在一个官方统一字段叫“`client_type=python`”。

更不等于存在公开参数可以把你变成某个官方 CLI。

如果你只是想让请求具备清晰、合法、可审计的“自家客户端身份”，建议只做下面这些：

| 字段 | 作用 | 建议 |
|---|---|---|
| `User-Agent` | 标明你的应用名、版本、运行环境 | 例如 `easyStory/0.1 (server; python)` |
| `X-Client-Request-Id` | 自己生成的单请求追踪 ID | OpenAI 官方明确支持；其他厂商可作为自家追踪头，但不能假设对方会记录 |
| `X-Trace-Id` / `X-Request-Id` | 你自己后端链路追踪 | 仅作为自家 tracing，不要冒充厂商返回的 request id |
| `OpenAI-Organization` / `OpenAI-Project` | OpenAI 侧路由到账户 / 项目 | 只在 OpenAI 官方支持时使用 |
| `anthropic-beta` | 开启 Claude beta 能力 | 仅在 Anthropic 文档明确列出的 beta feature 下使用 |

一个正常、自描述的服务端请求头示例：

```http
Authorization: Bearer <API_KEY>
Content-Type: application/json
User-Agent: easyStory/0.1 (server; python)
X-Client-Request-Id: 9d2d4d0c-1e9e-4c5e-b4cf-28d76ef2b109
X-Trace-Id: req_20260402_001
```

---

## 5. 关于“伪装成官方 CLI”

如果你的目标是“兼容官方协议”，做的是下面这些：

- 选对 `base_url`
- 选对 `api_dialect`
- 带对鉴权头
- 带对版本头 / beta 头
- 按对应协议序列化请求体

如果你的目标是“把请求伪装成某个官方产品”，这通常没有稳定、公开、可依赖的做法。

原因很简单：

- `User-Agent` 只是一个字符串，不等于完整客户端身份。
- 官方 CLI 往往还包含自己的认证流程、会话语义、重试策略、遥测、路径路由、功能开关和后端转发链路。
- 浏览器场景还会涉及 `Origin`、CORS、Cookie、`Sec-Fetch-*`、TLS 指纹等运行时上下文。

所以：

- 不要把“改 `User-Agent`”理解成“变成 Claude Code / Codex / Gemini CLI”。
- 如果你只是想做“Claude-like / Codex-like / Gemini-like”体验，应该复用它们的交互方式，而不是伪造它们的网络身份。

---

## 6. 浏览器直连时真正会多出什么

下面这些不是厂商私有参数，而是浏览器环境常见的网络特征：

- `Origin`
- `Referer`
- `Sec-Fetch-Site`
- `Sec-Fetch-Mode`
- `Sec-Fetch-Dest`
- `sec-ch-ua` / `sec-ch-ua-mobile` / `sec-ch-ua-platform`
- Cookie / SameSite / CORS preflight 行为

这里要特别说明：

- 这些头大多是浏览器根据页面上下文自动带上的，不是你在业务代码里随便“设一个字段”就能完全伪造出来。
- 很多自定义头在浏览器里会触发 CORS preflight；是否允许，取决于目标服务端响应头，而不是你前端想不想发。
- 因此“在浏览器里看起来像浏览器”不是厂商参数配置问题，而是运行时环境问题。

本节关于浏览器请求特征的描述，属于通用 HTTP / 浏览器行为推断，不对应某一家模型厂商的官方参数表。

---

## 7. 浏览器接入边界

对 easyStory 这类常规文本生成 / 多轮聊天产品，默认建议是：

- 标准 REST 文本接口全部走后端代理。
- 前端不要直接持有长效 API Key。
- 浏览器里只保留你自己的 session / JWT，不直接保留上游模型厂商主密钥。

当前官方明确给出“短期票据直连客户端”路径的主要有：

| 厂商 | 可直接给浏览器的官方短期票据 | 适用范围 | 备注 |
|---|---|---|---|
| OpenAI | `Realtime client secret` | Realtime API | 只适合 Realtime，不是通用 REST 文本接口 |
| Gemini | `ephemeral token` | Live API | 官方明确说目前只适用于 Live API |

对本文覆盖的常规文本 REST 接口：

- OpenAI：官方明确不建议把标准 API Key 暴露在浏览器或移动端。
- Gemini：官方明确不建议在生产环境把 API Key 直接放到前端；若要客户端直连，应优先看 Live API 的 ephemeral token。
- Claude / Kimi / MiniMax / GLM / DeepSeek：在本次核对到的官方文档里，没有看到面向标准文本 REST API 的浏览器短期票据方案，应按“服务端代理”处理。

---

## 8. easyStory 接入建议

建议把“请求参数”和“客户端身份”拆成两组内部字段，不要混成一个 `extra_headers` 大杂烩：

| 内部语义 | 建议 |
|---|---|
| `api_dialect` | 区分 `openai_responses / anthropic_messages / gemini_generate_content / openai_chat_completions` |
| `auth_strategy` | 区分 `bearer / x-api-key / x-goog-api-key / bearer-or-jwt` |
| `api_key_header_name` | 显式保存真实头名，不要靠 provider 名硬编码 |
| `user_agent_override` | 显式覆盖最终发送的 `User-Agent`，适合中转站要求特定客户端标识 |
| `client_name` | 你的产品名，例如 `easyStory` |
| `client_version` | 你的客户端版本，用于 `User-Agent` 和排错 |
| `runtime_kind` | 记录 `server-python / server-node / browser` |
| `request_id` | 每次请求唯一 ID，用于串联上游 request id 和自家日志 |
| `browser_access_mode` | 区分 `server_proxy / openai_realtime_client_secret / gemini_live_ephemeral` |
| `extra_headers` | 只放非敏感 metadata；不要拿它塞鉴权头 |

工程上最重要的约束：

1. 不要把“兼容 OpenAI SDK”误解成“兼容任意 OpenAI 风格客户端身份”。
2. 不要把 `User-Agent` 当作协议兼容层的主真值。
3. 浏览器接入要按“运行时边界”设计，不要按“头字符串长得像不像浏览器”设计。

当前 easyStory 运行时已按这套边界落地：

- `model_credentials` 正式保存 `user_agent_override / client_name / client_version / runtime_kind`
- 运行时若存在 `user_agent_override` 会优先直接发送它；没有时再根据 `client_name / client_version / runtime_kind` 自动生成 `User-Agent`
- Credential Center 提供 `Codex CLI / Claude Code / Gemini CLI / Chrome 浏览器` 这类客户端预设；预设本质上只是可编辑的 `User-Agent` 模板
- `extra_headers` 不允许覆盖 `User-Agent`

---

## 9. 官方来源

### OpenAI

- [API Overview](https://platform.openai.com/docs/api-reference/create-and-export-an-api-key)
- [Best Practices for API Key Safety](https://help.openai.com/en/articles/5112595-best-practices-for-api-key)
- [Realtime Client Secrets](https://platform.openai.com/docs/api-reference/realtime-sessions)
- [Realtime API with WebRTC](https://platform.openai.com/docs/guides/realtime-webrtc)

### Anthropic

- [API Overview](https://docs.anthropic.com/en/api/overview)
- [Messages API](https://docs.anthropic.com/en/api/messages)
- [Versions](https://docs.anthropic.com/en/api/versioning)
- [Beta Headers](https://docs.anthropic.com/en/api/beta-headers)

### Google Gemini

- [Using Gemini API Keys](https://ai.google.dev/gemini-api/docs/api-key)
- [OpenAI Compatibility](https://ai.google.dev/gemini-api/docs/openai)
- [Ephemeral Tokens](https://ai.google.dev/gemini-api/docs/ephemeral-tokens)

### Moonshot Kimi

- [API Reference](https://platform.moonshot.ai/docs/api-reference)

### MiniMax

- [文本合成原生接口](https://platform.minimaxi.com/docs/api-reference/text-post)
- [OpenAI API 兼容](https://platform.minimaxi.com/docs/api-reference/text-openai-api)

### Zhipu GLM

- [HTTP API 调用](https://docs.bigmodel.cn/cn/guide/develop/http/introduction)
- [模型概览](https://docs.bigmodel.cn/cn/guide/start/model-overview)

### DeepSeek

- [Your First API Call](https://api-docs.deepseek.com/)
- [DeepSeek API Authentication](https://api-docs.deepseek.com/api/deepseek-api)
- [Create Chat Completion](https://api-docs.deepseek.com/api/create-chat-completion)
