# 客户端身份、鉴权与请求头

| 字段 | 内容 |
|---|---|
| 文档类型 | 技术规范 / 请求头与客户端身份 |
| 文档状态 | 生效 |
| 创建时间 | 2026-04-10 |
| 更新时间 | 2026-04-10 |
| 关联文档 | [支持范围与治理规则](./supported-dialects-and-governance.md)、[请求契约](./request-contracts.md) |

---

## 1. 一个可移植 runtime 应该单独建模的连接字段

建议把连接层至少拆成这些字段：

- `protocol_family`
- `base_url`
- `auth_strategy`
- `api_key`
- `api_key_header_name`
- `client_name`
- `client_version`
- `runtime_kind`
- `user_agent_override`
- `extra_metadata_headers`

重点是把“鉴权”“客户端身份”“业务 metadata”三层分开，而不是全塞进一个自由 header map。

## 2. 4 个协议族的默认鉴权方式

| 协议族 | 默认鉴权方式 | 必需头 |
|---|---|---|
| `openai_responses` | `Authorization: Bearer <key>` | `Authorization`、`Content-Type` |
| `openai_chat_completions` | `Authorization: Bearer <key>` | `Authorization`、`Content-Type` |
| `anthropic_messages` | `x-api-key: <key>` | `x-api-key`、`anthropic-version`、`Content-Type` |
| `gemini_generate_content` | `x-goog-api-key: <key>` | `x-goog-api-key`、`Content-Type` |

Anthropic 官方 API 总览明确要求：

- `x-api-key`
- `anthropic-version`
- `content-type: application/json`

Gemini 官方 API Key 文档明确说明：

- REST 请求需要显式提供 API key
- REST 常用头是 `x-goog-api-key`

## 3. 兼容层不要滥改鉴权头

推荐规则：

- `bearer` 认证时，不要再允许任意自定义 header 名
- `x-api-key / x-goog-api-key` 这类协议专用头，也不要开放“随便改名”
- 只有在明确存在兼容网关要求时，才启用 `custom_header`

## 4. 客户端身份应该怎么建模

建议把客户端身份拆成：

- `client_name`
- `client_version`
- `runtime_kind`
- `user_agent_override`

推荐优先级：

1. 显式 `user_agent_override`
2. `client_name/client_version`
3. `client_name/client_version (runtime label)`

不要把 `User-Agent` 当成协议兼容真值；它只是身份自描述和排障辅助。

## 5. 推荐的 header 组装优先级

如果你要做一个可维护的 runtime，推荐按这个顺序组装请求头：

1. 协议强制头
2. 鉴权头
3. 明确的客户端身份头
4. 额外 metadata 头
5. transport 专用头
   - 例如 `Accept: text/event-stream`

## 6. 浏览器与服务端要分清

OpenAI 和 Gemini 官方文档都明确不建议把标准长效 API key 直接暴露给浏览器生产环境。

稳定做法：

- 标准文本 / 多轮聊天接口走服务端代理
- 浏览器只持有你自己的业务会话凭证
- 真正的厂商 API key 保留在服务端

当前官方明确给出浏览器短期票据路径的，主要是特定实时接口，不应误当成普通文本 REST 的通用规则。

## 7. “伪装客户端”不等于协议兼容

真正决定协议兼容性的，通常是：

- 请求体字段名
- 工具定义结构
- 响应体和流式事件
- 工具续接格式

不是：

- `User-Agent` 长得像不像某个官方 CLI
- 浏览器自动带不带 `Sec-Fetch-*`
- 请求头里有没有一串看上去“像官方产品”的标识

## 8. 对跨项目 agent runtime 的建议

- 把“官方必需头”“鉴权策略”“客户端身份”“业务 metadata”分开
- 对不同协议族保留默认鉴权策略，不要全都抽象成 `Bearer`
- 浏览器直连只在官方明确支持的场景下做
- 排障时记录上游 request id，但不要把返回头当成业务主真值

## 9. 一句话边界

请求头标准文档只回答“该带什么头、怎么建模身份”。  
某个项目里字段怎么命名、预设了哪些 UA 模板、UI 怎么展示，不属于这里的标准层。
