# 模型协议与工具调用标准

| 字段 | 内容 |
|---|---|
| 文档类型 | 技术规范 / 标准索引 |
| 文档状态 | 生效 |
| 创建时间 | 2026-04-10 |
| 更新时间 | 2026-04-10 |
| 关联文档 | [系统架构设计](../architecture.md)、[模型工具调用兼容层设计](../../design/23-provider-tool-interop-compatibility-layer.md)、[easyStory 采用映射](./easystory-adoption-profile.md) |

---

## 1. 目的

本目录分成两层：

- `标准层`
  - 可跨项目复用的模型协议与 agent runtime 参考
- `采用层`
  - easyStory 当前如何落地这些标准

如果你要把这些文档拿去别的项目做 agent，优先看标准层。  
如果你要核对 easyStory 当前代码和产品行为，再看采用层。

## 2. 标准层文档

这 5 篇是跨项目可复用的标准参考：

1. [支持范围与治理规则](./supported-dialects-and-governance.md)
2. [请求契约](./request-contracts.md)
3. [响应、流式与终态装配](./response-streaming-and-terminal-assembly.md)
4. [客户端身份、鉴权与请求头](./client-identity-auth-and-headers.md)
5. [工具调用、续接与一致性验证](./tool-calling-continuation-and-conformance.md)

它们只保留：

- 官方协议事实
- 可移植的 runtime 设计建议
- 跨协议最稳定的最小交集

它们不直接承载：

- easyStory 的字段名
- easyStory 的按钮文案
- easyStory 的项目工具面
- easyStory 的数据库持久化列

## 3. 一页总览

| 维度 | `openai_responses` | `openai_chat_completions` | `anthropic_messages` | `gemini_generate_content` |
|---|---|---|---|---|
| 默认鉴权 | `Authorization: Bearer` | `Authorization: Bearer` | `x-api-key` | `x-goog-api-key` |
| 请求主字段 | `input` | `messages` | `messages` + 顶层 `system` | `contents` + `systemInstruction` |
| 输出上限字段 | `max_output_tokens` | 官方 OpenAI 用 `max_completion_tokens`，兼容网关多用 `max_tokens` | `max_tokens` | `generationConfig.maxOutputTokens` |
| continuation 模式 | `hybrid` | `runtime_replay` | `runtime_replay` | `runtime_replay` |
| 工具结果回传 | `function_call_output` | `role=tool` message | `tool_result` content block | `functionResponse` part |
| 流式终态 | `response.completed` | final chunk + `[DONE]` | `message_stop` | `streamGenerateContent` SSE 末尾 payload |

## 4. 采用层文档

这篇是 easyStory 当前项目采用映射：

- [easyStory 采用映射](./easystory-adoption-profile.md)

它记录的是：

- 当前项目的字段名
- 当前项目的 `interop_profile`
- 当前项目的工具能力验证字段
- 当前项目的 `project.*` 工具面
- 当前项目的 Gemini 流式补丁与门控实践

## 5. 维护原则

- 新增或修改跨项目可复用的协议规则时，先改标准层文档
- 某个项目自己的实现细节，只写进采用层文档
- 某个渠道的临时兼容性，不要污染标准层
- 旧的宽口径 provider 资料仍保留在 `docs/specs/` 根目录，作为扩展参考，不替代这里的标准层

## 6. 相关旧文档

以下文档继续保留，但角色调整为扩展资料或市场参考：

- [主流模型厂商请求参数参考](../model-provider-request-params-reference.md)
- [主流模型厂商响应结构与流式事件参考](../model-provider-response-contract-reference.md)
- [主流模型厂商请求头与客户端标识参考](../model-provider-client-identity-and-headers-reference.md)
