# 工具调用、续接与一致性验证

| 字段 | 内容 |
|---|---|
| 文档类型 | 技术规范 / 工具调用标准 |
| 文档状态 | 生效 |
| 创建时间 | 2026-04-10 |
| 更新时间 | 2026-04-10 |
| 关联文档 | [请求契约](./request-contracts.md)、[响应、流式与终态装配](./response-streaming-and-terminal-assembly.md)、[easyStory 采用映射](./easystory-adoption-profile.md) |

---

## 1. canonical tool contract

一个可移植的 agent runtime，建议先把工具能力抽象成 canonical contract：

- `canonical_tool_name`
- `canonical_tool_schema`
- `canonical_tool_call`
- `canonical_tool_result`
- `canonical_continuation_items`

业务层不应直接依赖这些 provider-specific 结构：

- `function_call_output`
- `tool_use`
- `tool_result`
- `functionCall`
- `functionResponse`

这些都属于协议适配层。

## 2. 工具名策略

推荐做法：

- 内部工具名可以保留业务语义，例如 dotted name
- 外发时统一转成安全 ASCII alias
- 响应解析时再反解回 canonical name

为什么这样做：

- Anthropic 官方要求工具名符合 `^[a-zA-Z0-9_-]{1,64}$`
- OpenAI / 兼容网关普遍对安全 ASCII 名更稳定
- Gemini 官方虽然主要给的是命名最佳实践，但也明确建议避免空格、句点和连字符

因此，跨协议最稳的策略是：

- 只用字母、数字、下划线、连字符
- 控制长度
- 冲突时追加短 hash

## 3. 工具 schema 的可移植最小交集

跨 OpenAI / Anthropic / Gemini 时，最稳定的 schema 写法建议是：

- root 使用 `object`
- 只用常见 JSON Schema / OpenAPI 基本类型
- 明确 `required`
- 避免复杂组合 schema 作为默认路径
- 不依赖任意开放对象

Gemini 官方文档明确提醒：

- 只支持 OpenAPI schema 的一个子集
- `ANY` 模式下，大 schema、深层嵌套 schema 容易被拒绝

## 4. 四个协议族的工具调用映射

| 协议族 | 工具声明 | 模型返回 tool call | 工具结果回传 |
|---|---|---|---|
| `openai_responses` | `tools[]` | `output[].function_call` | `function_call_output` |
| `openai_chat_completions` | `tools[].function` | `message.tool_calls[]` / `delta.tool_calls[]` | `role=tool` message |
| `anthropic_messages` | `tools[].input_schema` | `content[].tool_use` | `content[].tool_result` |
| `gemini_generate_content` | `tools[].functionDeclarations[]` | `parts[].functionCall` | `parts[].functionResponse` |

## 5. continuation 模型

跨项目 runtime 通常至少要支持两类 continuation：

- `provider continuation`
  - 利用上游提供的 continuation id 或对话状态
- `runtime replay`
  - 本地保留最近一轮 tool call / tool result / assistant message，再投影回下一轮请求

推荐策略：

- 即使某个协议支持 provider continuation，也保留一份 runtime 自己的 canonical continuation items
- 把“协议层 continuation 能力”和“业务层 run/step 恢复真值”分开

## 6. conformance probe 的推荐分层

要判断一条连接是否真的适合开工具，不应只做文本探活。

推荐至少分 4 层：

1. `text_probe`
   - 验证基本文本生成
2. `tool_definition_probe`
   - 验证工具声明会被协议接受
3. `tool_call_probe`
   - 验证模型会真实返回 tool call
4. `tool_continuation_probe`
   - 验证 tool result 回传后能继续推理

这是跨项目最值得保留的能力验证模型之一，因为它能直接暴露“文本能生成，但完整 tool loop 不可用”的真实问题。

## 7. transport 维度必须单独验证

流式和非流式工具能力不能天然视为等价。

推荐做法：

- 分别验证 `buffered` tool loop
- 分别验证 `streaming` tool loop
- 分别持久化这两类能力结论

原因：

- 一些渠道非流工具可用，但流式终态装配会失败
- 工具解析、usage 收束、终态判断在 stream 与 buffered 下不是一回事

## 8. 工具信任与审批模式

推荐把工具至少按这三维建模：

- `plane`
  - `resource` / `mutation`
- `trust_class`
  - 本地一方工具 / 远程工具 / 第三方工具
- `approval_mode`
  - `none`
  - `grant_bound`
  - `always_confirm`

通用建议：

- 只读资源工具默认可以 `approval_mode=none`
- 写操作、外部副作用、不可逆动作不要默认自动执行
- 如果要做“本轮临时授权后写回”，可以使用 `grant_bound`
- 如果必须等用户逐次确认，再用 `always_confirm`

## 9. 工具结果设计建议

通用 tool result 建议至少保留：

- `status`
- `structured_output`
- `display_content`
- `error`
- `audit`

原则：

- 让模型继续推理所需的真值放在 `structured_output`
- 给人看的摘要是投影，不应替代结构化真值
- 错误必须带明确 code，不要只给一句模糊文本

## 10. 官方文档与实践综合后的几个关键坑

- 文本验证成功，不代表完整 tool loop 可用
- 工具名若不做安全 alias，很多网关会在工具请求阶段直接失败
- 复杂 schema 往往比工具本身更早成为失败点
- Gemini 流式下不能只看最后一个 payload判断有没有 tool call
- 并行工具调用虽然有的协议支持，但本地 runtime 如果没有严格的幂等和恢复模型，默认应保守关闭

## 11. 一句话边界

工具调用标准文档只回答“如何做一个跨协议稳定的 tool loop”。  
某个项目当前有哪些工具、写入授予条件是什么、字段怎么命名，应该放到 adoption profile。
