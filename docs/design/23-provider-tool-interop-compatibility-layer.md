# 模型工具调用兼容层设计

| 字段 | 内容 |
|---|---|
| 文档类型 | 功能设计 |
| 文档状态 | 部分落地 |
| 创建时间 | 2026-04-08 |
| 更新时间 | 2026-04-10 |
| 关联文档 | [22-assistant-tool-calling-runtime](./22-assistant-tool-calling-runtime.md)、[21-assistant-project-document-tools](./21-assistant-project-document-tools.md)、[模型协议与工具调用标准](../specs/model-protocols/README.md)、[系统架构设计](../specs/architecture.md)、[模型协议兼容中间层重构方案](../plans/2026-04-07-model-provider-compatibility-middleware-plan.md) |

---

> 本文档定义 easyStory 在 ordinary chat / assistant tool-calling / provider interop probe / credential verifier 之间共享的“模型工具调用兼容层”长期目标设计。
>
> 当前代码里已经存在一版协议兼容中间层，但它还没有把“内部工具语义”和“外部协议格式”彻底隔离。本文关注的是最终稳定形态，不是一次性补丁。
>
> 截至 `2026-04-10`，tool name alias codec、conformance probe、凭证 `interop_profile -> verifier -> assistant runtime -> Credential Center` 贯通、assistant visible-tools capability gating、Credential Center 显式 `验证连接 / 验证流式工具 / 验证非流工具` 产品语义，以及 Gemini 流式 tool-call terminal synthesis 都已落地；后续仍需继续推进更细粒度的 gateway profile。

## 1. 目的

定义一套长期稳定、可维护、可验证的模型工具调用兼容层，使 easyStory 后续接入：

- OpenAI / Codex
- Anthropic Claude
- Google Gemini
- Qwen / Kimi / DeepSeek / GLM / MiniMax 等 OpenAI-compatible 网关

时，不需要继续把协议差异散落到：

- `AssistantService`
- `AssistantToolLoop`
- `LLMToolProvider`
- provider interop probe
- credential verifier

本文的核心目标不是“再包一层抽象”，而是建立一条清晰边界：

1. 业务层只表达内部稳定语义
2. 协议边界层负责外发格式、回包解析、流式事件、tool continuation 与网关差异
3. 新增 provider / gateway 时，优先新增 profile 与 conformance case，而不是在业务层继续打分支

## 2. 直接触发原因

### 2.1 2026-04-08 的真实问题

截至 `2026-04-08`，创作工作台共创助手暴露出以下现象：

- Gemini 渠道在同一项目、同一问题、同一文稿上下文下可以正常触发 `project.search_documents`
- `bwen` 渠道的 `gpt-5.4` 会在 assistant tool 场景下失败
- 失败不是凭证层“连不上上游”，而是 assistant 发起带 tools 的模型请求后，上游返回错误

现有失败快照可见：

- [74fbca0a-21e0-5bee-8137-74783647a7ed.json](./../../apps/api/.runtime/assistant-config/turn-runs/74fbca0a-21e0-5bee-8137-74783647a7ed.json#L774)

其中明确记录：

- `terminal_error_code = configuration_error`
- `terminal_error_message = LLM streaming request failed: HTTP 502 - {"error":{"message":"Upstream request failed","type":"upstream_error"}}`

### 2.2 本地直连自测结论

在 `2026-04-08` 的本地直连测试里，使用同一条 `bwen` 凭证，对上游做了最小请求验证：

1. 当前内部工具名是 dotted name，例如 `project.search_documents`
2. 以该名字请求 `openai_responses` 时，哪怕只保留最小参数 schema，也会返回 `502 upstream_error`
3. 同一上游改走 `openai_chat_completions` 时，会明确报 `400`，提示函数名不符合 `^[a-zA-Z0-9_-]+$`
4. 只把外发工具名改成 `project_search_documents` 后，不改业务逻辑，`openai_responses` 与 `openai_chat_completions` 都能成功触发 tool call

因此这次问题的根因不是：

- assistant tool loop 本地执行器坏了
- SSE reader 坏了
- 上游模型完全不支持工具调用

真正根因是：

- **当前内部 canonical tool name 被直接外发到了 provider 协议边界**
- **现有兼容层还没有把“内部工具标识”和“外部函数名约束”彻底解耦**

### 2.3 当前设计暴露出的结构性问题

这次问题同时说明了三件事：

1. 连接验证成功，不等于 assistant tool-calling 可用  
   现有 verifier 主要验证“纯文本可生成”，没有验证“带 tools 的完整 contract”
2. 只按 `api_dialect` 分支，不足以表达真实网关差异  
   自称 OpenAI-compatible 的网关，不等于完整兼容 OpenAI Responses / Chat 的全部工具契约
3. 兼容层还停留在“请求 builder / 响应 parser”级别  
   但长期稳定所需的边界，已经必须提升到“内部语义 contract 与外部协议 contract 分离”

## 3. 当前代码基线

当前仓库里已经有一套共享的 LLM 协议兼容中间层，主要入口在：

- 请求构造：[llm_protocol_requests.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/llm_protocol_requests.py)
- 非流式解析：[llm_protocol_responses.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/llm_protocol_responses.py)
- 流式事件归一化：[llm_stream_events.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/llm_stream_events.py)
- 流式终态装配：[llm_terminal_assembly.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/llm_terminal_assembly.py)
- assistant 统一 LLM 调用入口：[llm_tool_provider.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/llm_tool_provider.py)
- provider interop facade：[provider_interop_stream_support.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/interop/provider_interop_stream_support.py)
- 凭证验证入口：[verifier.py](/home/zl/code/easyStory/apps/api/app/modules/credential/infrastructure/verifier.py)

assistant 侧与工具域的正式入口在：

- assistant 主链：[assistant_service.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/assistant_service.py)
- tool loop：[assistant_tool_loop.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/tooling/assistant_tool_loop.py)
- tool descriptor registry：[assistant_tool_registry.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/tooling/assistant_tool_registry.py)
- tool executor：[assistant_tool_executor.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/tooling/assistant_tool_executor.py)

当前实现的优点是：

- 已经按协议族区分了 `openai_responses / openai_chat_completions / anthropic_messages / gemini_generate_content`
- assistant / verifier / probe 已共享同一套 transport 与 parser
- tool loop、run/step 真值、stream event、continuation 已有统一 runtime

当前实现的不足是：

- tool continuation 与部分协议回放细节仍然贴近具体 provider contract
- `tool_schema_compiler` 已落地，但更细粒度的 schema / strict gateway profile 仍未完全展开
- gateway profile 目前仍偏粗粒度，尚未覆盖更多代理方言差异

### 3.1 当前已落地进展（2026-04-10）

- shared runtime 已建立 canonical dotted tool name -> external safe alias 的统一边界
- `provider_interop_check.py` 已支持 `text_probe / tool_definition_probe / tool_call_probe / tool_continuation_probe`
- `ModelCredential` 现已支持持久化 `interop_profile`
- `AsyncHttpCredentialVerifier`、assistant runtime 与 `LLMToolProvider` 已共享同一份 `interop_profile`
- Credential Center 已暴露 `interop_profile` 配置入口，并按 `api_dialect` 约束可选项
- `/api/v1/credentials/{id}/verify` 已支持显式 `probe_kind`
- Credential Center 已显式区分 `验证连接(text_probe)`、`验证流式工具(tool_continuation_probe + stream)` 与 `验证非流工具(tool_continuation_probe + buffered)`
- `ModelCredential` 当前按 transport mode 分别持久化 `stream_tool_verified_probe_kind` 与 `buffered_tool_verified_probe_kind`
- assistant runtime 在存在 visible tools 时会按当前 transport mode 显式要求 `tool_continuation_probe`，不再把所有已验证连接默认为支持 project tools
- shared runtime 已新增 `tool_schema_compiler.py`，OpenAI / Claude / Gemini 的 tool definitions 统一走 `tool_schema_mode`
- 当前 `portable_subset` 会收口 required-only `anyOf`，`gemini_compatible` 会在此基础上继续移除 Gemini 不支持的 schema key
- shared runtime 已新增 `tool_continuation_codec.py`，runtime replay projection、tool result payload encoding 与 OpenAI Responses continuation input 已从 request builder 中抽离
- shared runtime 已为 Gemini 流式补齐终态 tool-call synthesize，避免早期 `functionCall` 在 terminal 装配时丢失或重复

## 4. 设计目标

本方案要求：

1. assistant 业务层不再直接承担 provider-specific tool 协议差异
2. 内部 tool id、tool schema、tool result、continuation 形成唯一 canonical contract
3. 外部协议差异全部收口到共享兼容层
4. OpenAI / Codex、Claude、Gemini、以及 OpenAI-compatible 网关都能落入统一架构
5. 新增网关时，优先补 capability profile 和 conformance case，不再修改 assistant 主流程
6. 连接验证与真实可用能力一致，不再出现“文本验证成功但 tool 场景必挂”的漂移
7. 所有失败都显式暴露，不引入静默 fallback

本方案不追求：

- 一开始就把所有厂商做成 vendor-native dialect
- 在业务层保留 dotted name 直通上游的兼容写法
- 为了“能跑”而在运行时静默降级成纯文本模式

## 5. 长期硬边界

### 5.1 业务层只认 canonical contract

assistant、workflow、incubator、verifier 在业务层长期只认：

- canonical tool id
- canonical tool arguments / tool result
- canonical continuation items
- canonical normalized output items

业务层不认：

- `function_call_output`
- `tool_use`
- `functionResponse`
- `message.tool_calls`
- `response.output[]`

这些都属于协议边界实现细节。

### 5.2 协议边界必须可逆

兼容层不是只负责“发出去”，还必须保证：

- 内部 canonical tool id 可以稳定映射成外部安全名字
- 外部模型返回的 tool name / tool call id 可以可靠映射回内部 canonical tool id
- continuation 中引用的 `call_id`、`provider_ref`、`response_id` 不会在跨协议轮次里漂移

### 5.3 gateway 差异属于 profile，不属于业务分支

`bwen`、Qwen、Kimi、DeepSeek、MiniMax、GLM 这类差异，不应继续体现在：

- `if provider == "xxx"`
- `if base_url contains "xxx"`
- `if model_name startswith "xxx"`

长期应该只表现为：

- `protocol_family`
- `tool_name_policy`
- `schema_mode`
- `stream_terminal_shape`
- `continuation_mode`
- `strict_default`

### 5.4 验证层必须覆盖 tool contract

连接级验证至少要区分：

- 纯文本生成是否可用
- tool definition 是否被接受
- tool call 是否会按预期返回
- tool result continuation 是否可继续推理

只有验证通过的能力，才能在产品层显式开启。

## 6. 外部协议族一览

### 6.1 OpenAI / Codex：`Responses API`

这是 OpenAI 官方当前推荐的新项目主协议，也是 GPT-5.4 / Codex-like agentic 流程最完整的 tool-using 入口。

#### 请求中的工具定义

```json
{
  "model": "gpt-5.4",
  "input": [...],
  "tools": [
    {
      "type": "function",
      "name": "get_weather",
      "description": "Retrieve weather.",
      "parameters": { "type": "object", "properties": {}, "required": [] },
      "strict": true
    }
  ]
}
```

#### 模型返回的工具调用

- 非流式：`response.output[]` 中 `type=function_call`
- 流式：
  - `response.output_item.added`
  - `response.function_call_arguments.delta`
  - `response.function_call_arguments.done`
  - `response.completed`

#### 应用回传工具结果

```json
{
  "type": "function_call_output",
  "call_id": "call_123",
  "output": "{\"ok\":true}"
}
```

#### 关键约束

- 函数名只能包含字母、数字、下划线、连字符，最长 64
- `Responses` 默认更接近 strict tool schema 语义
- tool continuation 优先使用 `previous_response_id + function_call_output`

### 6.2 OpenAI-compatible：`Chat Completions`

这是最常见的兼容层协议，但不是 OpenAI 当前推荐的新项目主接口。很多第三方网关仍以它为主。

#### 请求中的工具定义

```json
{
  "model": "gpt-5.4",
  "messages": [...],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Retrieve weather.",
        "parameters": { "type": "object", "properties": {}, "required": [] },
        "strict": true
      }
    }
  ]
}
```

#### 模型返回的工具调用

- 非流式：`choices[0].message.tool_calls[]`
- 流式：`choices[0].delta.tool_calls[]`

#### 应用回传工具结果

```json
{
  "role": "tool",
  "tool_call_id": "call_123",
  "content": "{\"ok\":true}"
}
```

#### 关键约束

- 函数名同样只允许字母、数字、下划线、连字符
- continuation 依赖 assistant replay，而不是 `previous_response_id`
- 同类网关对 strict/schema/stream usage 的支持程度不一致

### 6.3 Anthropic Claude：`Messages API + tools`

Claude 原生不是 OpenAI Chat，也不是 Responses。它的 tools 是 content blocks 语义。

#### 请求中的工具定义

```json
{
  "model": "claude-sonnet-4-6",
  "system": "...",
  "messages": [...],
  "tools": [
    {
      "name": "get_weather",
      "description": "Retrieve weather.",
      "input_schema": { "type": "object", "properties": {}, "required": [] }
    }
  ]
}
```

#### 模型返回的工具调用

- 非流式：assistant `content[]` 中 `type=tool_use`
- 流式：`content_block_start / content_block_delta / content_block_stop`

#### 应用回传工具结果

```json
{
  "role": "user",
  "content": [
    {
      "type": "tool_result",
      "tool_use_id": "toolu_123",
      "content": "{\"ok\":true}"
    }
  ]
}
```

#### 关键约束

- 工具名必须符合 `^[a-zA-Z0-9_-]{1,64}$`
- `tool_result` 必须与对应 `tool_use` 保持强关联
- Claude continuation 更接近 runtime replay，不适合简单照搬 OpenAI Responses 的 provider continuation

### 6.4 Gemini：`functionDeclarations + functionCall/functionResponse`

Gemini 原生也不是 OpenAI 结构。它走 `contents / parts / functionCall / functionResponse` 语义。

#### 请求中的工具定义

```json
{
  "contents": [...],
  "tools": [
    {
      "functionDeclarations": [
        {
          "name": "getWeather",
          "description": "Retrieve weather.",
          "parameters": { "type": "object", "properties": {}, "required": [] }
        }
      ]
    }
  ]
}
```

#### 模型返回的工具调用

- 非流式：`candidates[].content.parts[].functionCall`
- 流式：SSE / stream response 中逐步生成 `functionCall`

#### 应用回传工具结果

```json
{
  "role": "user",
  "parts": [
    {
      "functionResponse": {
        "name": "getWeather",
        "id": "call_123",
        "response": { "result": "ok" }
      }
    }
  ]
}
```

#### 关键约束

- 官方最佳实践明确建议函数名不要使用空格、句点、连字符，优先下划线或 camelCase
- 只支持 OpenAPI / JSON Schema 的一个子集
- 大 schema、深嵌套 schema、复杂 `anyOf/oneOf` 风险较高

### 6.5 OpenAI-compatible 网关不是新的协议族

像 Qwen / Kimi / DeepSeek / GLM / MiniMax 这类网关，在 easyStory 长期设计里不应该直接被视为新的业务协议族。

它们应该被建模为：

- `protocol_family = openai_responses`
或
- `protocol_family = openai_chat_completions`

再叠加 profile，例如：

- 只接受安全工具名
- 对 strict schema 支持不完整
- stream terminal shape 有变体
- usage 位置有差异

## 7. 协议族与网关差异矩阵

| 维度 | OpenAI / Codex Responses | OpenAI-compatible Chat | Claude | Gemini | OpenAI-compatible 网关 |
|---|---|---|---|---|---|
| 请求主字段 | `input` / `instructions` / `tools` | `messages` / `tools` | `messages` / 顶层 `system` / `tools` | `contents` / `tools.functionDeclarations` | 跟随某个协议族 |
| 模型工具调用 | `output[].function_call` | `message.tool_calls[]` | `content[].tool_use` | `parts[].functionCall` | 跟随某个协议族，但细节不一定完整 |
| 工具结果回传 | `function_call_output` | `role=tool` message | `tool_result` block | `functionResponse` part | 跟随某个协议族，但约束更严格或更弱 |
| 流式终态 | `response.completed` | `[DONE]` / final chunk | `message_stop` | 流结束 + 完整 response | 高度不稳定 |
| 工具名约束 | 安全 ASCII 名，最长 64 | 安全 ASCII 名，最长 64 | 安全 ASCII 名，最长 64 | 官方建议禁用空格、句点、连字符 | 不得假设比官方更宽松 |
| schema 支持 | strict 子集 | 通常弱于 Responses | `input_schema` | OpenAPI subset | 漂移最大 |
| continuation | provider continuation 友好 | runtime replay 为主 | runtime replay 为主 | runtime replay 为主 | 逐 profile 判断 |

## 8. 最终架构

### 8.1 总览

```text
Assistant / Workflow / Verifier / Probe
  -> Canonical Semantic Contract
    -> Protocol Family Adapter
      -> Gateway Capability Profile
        -> HTTP / SSE Transport
```

### 8.2 第 1 层：Canonical Semantic Contract

这一层是内部唯一真值。

它至少统一这些对象：

- `canonical_tool_id`
- `canonical_tool_definition`
- `canonical_tool_call`
- `canonical_tool_result`
- `canonical_continuation_items`
- `canonical_stream_events`

内部 canonical tool id 继续允许使用业务语义名，例如：

- `project.list_documents`
- `project.search_documents`
- `project.read_documents`

这些名字只在 easyStory 内部存在，不再直接外发给 provider。

### 8.3 第 2 层：Protocol Family Adapter

这一层只处理 4 个协议族：

- `openai_responses`
- `openai_chat_completions`
- `anthropic_messages`
- `gemini_generate_content`

每个 adapter 负责：

1. 把 canonical tool definition 编码成该协议的请求格式
2. 把模型返回的 tool call 解码回 canonical tool call
3. 把本地 tool result 编码成该协议支持的 continuation 格式
4. 统一 stream delta、arguments delta、terminal payload

### 8.4 第 3 层：Gateway Capability Profile

这一层不再看 provider 名字，而是看能力。

建议 profile 至少表达：

- `profile_id`
- `protocol_family`
- `tool_name_policy`
- `schema_mode`
- `strict_default`
- `supports_stream_tool_arguments`
- `supports_provider_continuation`
- `supports_parallel_tool_calls`
- `supports_reasoning_delta`
- `stream_terminal_shape`
- `usage_shape`

例如 `bwen` 这类连接，长期不应该只记录：

- `api_dialect = openai_responses`

而应该记录成：

- `protocol_family = openai_responses`
- `tool_name_policy = safe_ascii_only`
- `schema_mode = strict_subset`
- `stream_terminal_shape = responses_standard`

### 8.5 第 4 层：Conformance Verification

这一层负责把“连接是否可用”升级成“能力是否可用”。

建议固定四类 probe：

1. `text_probe`
2. `tool_definition_probe`
3. `tool_call_probe`
4. `tool_continuation_probe`

只有通过对应 probe 的连接，才允许启用对应运行模式。

## 9. Canonical Contract 设计

### 9.1 Canonical Tool ID 与 External Alias

内部工具 id 与外部工具名必须彻底解耦。

建议规则：

- 内部 id 保留 dotted name
- 外部 alias 统一转成安全 ASCII 名
- alias 必须稳定、可逆、可去重

示例：

| 内部 canonical id | 外部 alias |
|---|---|
| `project.search_documents` | `project_search_documents` |
| `project.read_documents` | `project_read_documents` |
| `project.list_documents` | `project_list_documents` |

若出现冲突，再追加短 hash，而不是回退成原始 dotted name。

### 9.2 Canonical Continuation Items

内部 continuation 不应绑定某个 provider 的消息格式。

建议继续维持统一 item taxonomy：

- `text`
- `tool_call`
- `tool_result`
- `reasoning`
- `refusal`

adapter 再分别把它们编码成：

- OpenAI Responses `function_call_output`
- OpenAI Chat `role=tool`
- Claude `tool_result`
- Gemini `functionResponse`

### 9.3 Canonical Stream Events

流式也必须统一成内部事件，而不是直接把厂商 event name 往上传。

建议 canonical stream event 至少包括：

- `text_delta`
- `tool_call_started`
- `tool_arguments_delta`
- `tool_call_completed`
- `terminal_response`

## 10. 建议新增的兼容层模块

建议在 `app/shared/runtime/llm/interop/` 下新增以下模块：

- `tool_name_codec.py`
- `tool_schema_compiler.py`
- `tool_call_codec.py`
- `tool_result_codec.py`
- `tool_continuation_codec.py`
- `stream_event_normalizer.py`
- `provider_capability_profiles.py`

各自职责如下：

### 10.1 `tool_name_codec.py`

- canonical tool id -> external alias
- external alias -> canonical tool id
- 保证稳定、可逆、可去重

### 10.2 `tool_schema_compiler.py`

- 从 canonical schema 编译到协议可接受 schema
- 不再把 Gemini 特判散落在 request builder
- 严格限制公共 assistant tool contract 使用可移植子集

### 10.3 `tool_call_codec.py`

- 统一解析外部 tool call
- 恢复 canonical tool id
- 保留 `call_id / provider_ref / arguments_text / arguments_error`
- 当前 shared runtime 已用它收口 `llm_protocol_responses.py` 的 OpenAI / Claude / Gemini tool call parse，stream terminal 解析也复用同一条 codec

### 10.4 `tool_result_codec.py`

- 把内部 tool result 编码成各协议 continuation 格式
- 统一处理结构化输出与文本输出

### 10.5 `stream_event_normalizer.py`

- 统一解析 text delta、arguments delta、stop reason、terminal payload
- 把不同协议流式事件转成同一组内部 stream event
- 当前 shared runtime 已用它收口 `llm_stream_events.py` 的协议分支；`provider_interop_stream_support.py` 继续只消费 facade，不再直接承载 provider-specific parse 逻辑

### 10.6 `provider_capability_profiles.py`

- 管理协议族内变体
- 明确记录每种 gateway 的边界条件

## 11. 统一能力约束

为了获得跨协议最稳定的 assistant tool surface，公共工具 contract 需要收口到可移植子集。

建议公共 assistant tool schema 长期遵守：

1. root 必须是 `object`
2. 只使用 `string / integer / number / boolean / array / object / enum`
3. `additionalProperties = false`
4. 不依赖复杂 `anyOf / oneOf / allOf / not / patternProperties`
5. 嵌套深度和字段数做上限
6. 可选参数优先通过拆工具或显式 mode 表达，而不是依赖复杂 schema 逻辑

原因不是“为了迁就最弱 provider”，而是：

- 这是 OpenAI / Claude / Gemini 共同最稳定的交集
- 也是长期维护成本最低的公共 contract

## 12. 验证模型

### 12.1 Probe 分类

建议所有连接统一跑：

| Probe | 目的 | 通过后允许的能力 |
|---|---|---|
| `text_probe` | 验证纯文本生成 | 普通聊天 |
| `tool_definition_probe` | 验证 tools 能被接受 | 开启 tool 模式准备 |
| `tool_call_probe` | 验证模型能真实返回 tool call | 开启只读工具 |
| `tool_continuation_probe` | 验证 tool result 回传后能继续推理 | 开启完整 tool loop |

当前 probe 契约还需要保持两条硬规则，避免假阳性污染 capability 真值：

- `tool_definition_probe` 必须返回精确 success token，且不允许把任意非空文本或额外 tool call 视为成功
- `tool_continuation_probe` 的最终回答必须包含只存在于 tool result 中的动态 echoed 值，不能把期望答案直接写进 follow-up prompt

### 12.2 产品侧能力门控

assistant runtime 不应再把所有已验证连接默认视为“支持 project tools”。

明确门控建议：

- 只通过 `text_probe`
  - 只允许普通聊天
- 通过 `tool_definition_probe + tool_call_probe`
  - 可允许只读工具试运行
- 通过 `tool_continuation_probe`
  - 才允许完整 tool loop

### 12.3 当前已落地门控真值

截至 `2026-04-10`，产品已按以下口径落地：

- `last_verified_at` 只表示文本连接验证状态
- `stream_tool_verified_probe_kind` 保存“当前最高已证明的流式工具 capability”
- `buffered_tool_verified_probe_kind` 保存“当前最高已证明的非流工具 capability”
- 连接级关键字段变更（如 `api_key / base_url / default_model / api_dialect / interop_profile / headers / user-agent`）会显式清空文本和工具验证真值
- verifier 成功后会按 probe 等级做 promote，不会因为再次执行较低等级 probe 而降级；该 promote 需要基于数据库当前值做原子更新，不能只依赖应用层内存对象
- assistant prepare 阶段在存在 visible tools 时，会根据当前 transport mode 显式要求对应侧的 `tool_continuation_probe`
- 能力不足时直接返回显式业务错误，引导用户先执行“验证工具”，不做静默隐藏工具或自动降级到纯文本

## 13. 与现有代码的衔接原则

本方案不是推翻现有实现，而是在当前基线之上继续收口。

优先改造的边界点是：

- [llm_protocol_requests.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/llm_protocol_requests.py)
- [llm_protocol_responses.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/llm_protocol_responses.py)
- [llm_stream_events.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/llm_stream_events.py)
- [llm_terminal_assembly.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/llm_terminal_assembly.py)
- [llm_tool_provider.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/llm_tool_provider.py)

assistant 业务层应尽量少改：

- [assistant_service.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/assistant_service.py)
- [assistant_tool_loop.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/tooling/assistant_tool_loop.py)
- [assistant_tool_executor.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/tooling/assistant_tool_executor.py)

这也是本文坚持“兼容层收口到 shared/runtime/llm”而不是继续把差异下沉到 assistant 域的原因。

## 14. 改造原则

后续实施必须遵守：

1. 不把 dotted canonical id 改成外部安全名作为内部真值
2. 不在 assistant 业务层继续增加 provider-specific 条件分支
3. 不以静默 fallback 方式绕过 tool contract 问题
4. 不以“某个网关刚好能用”来替代正式 capability profile
5. 不再让连接验证只覆盖纯文本而忽略工具契约

## 15. 为什么这是长期最稳的方案

这套设计的稳定性来自四点：

1. **边界清晰**  
   业务层、协议层、网关差异层、验证层各自有单一职责
2. **新增 provider 成本低**  
   新增 provider 时优先补 profile 与 conformance case，不需要改主流程
3. **排障可定位**  
   出问题时能明确定位到 name codec、schema compiler、continuation codec 或 stream normalizer
4. **文档与实现一致**  
   以后维护时，不再需要同时在 assistant、probe、verifier、parser 四处猜测真实契约

这不是“最省事”的方案，但它是**后续维护最容易、长期最稳定**的方案。

## 16. 外部官方参考

### 16.1 OpenAI / Codex

- OpenAI Function Calling: <https://platform.openai.com/docs/guides/function-calling>
- OpenAI API Reference: <https://platform.openai.com/docs/api-reference/chat/create>

本轮结论采用的官方口径包括：

- 新项目推荐 `Responses API`
- function tool 支持 strict mode
- function name 只允许字母、数字、下划线、连字符，最长 64

### 16.2 Anthropic Claude

- Claude Tool Use: <https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/implement-tool-use>

本轮结论采用的官方口径包括：

- 工具定义使用 `name + description + input_schema`
- 工具名必须符合 `^[a-zA-Z0-9_-]{1,64}$`
- 工具结果通过 `tool_result` content block 回传

### 16.3 Google Gemini

- Gemini Function Calling: <https://ai.google.dev/gemini-api/docs/function-calling>

本轮结论采用的官方口径包括：

- 工具定义使用 `functionDeclarations`
- 返回使用 `functionCall / functionResponse`
- 只支持 OpenAPI / JSON Schema 子集
- 官方最佳实践明确建议工具名不要使用空格、句点、连字符
