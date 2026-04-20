# 模型协议兼容中间层重构方案

| 字段 | 内容 |
|---|---|
| 文档类型 | 实施方案 |
| 文档状态 | 首轮实施完成 |
| 创建时间 | 2026-04-07 |
| 更新时间 | 2026-04-07 |
| 关联文档 | [主流模型厂商请求参数参考](../specs/model-provider-request-params-reference.md)、[主流模型厂商响应结构与流式事件参考](../specs/model-provider-response-contract-reference.md)、[Assistant 主路径](../design/20-assistant-runtime-chat-mode.md)、[Assistant 原生 Tool-Calling Runtime](../design/22-assistant-tool-calling-runtime.md) |

---

## 0. 当前实施状态

截至 `2026-04-07`，当前方案在代码里的首轮实施状态是：

- **Phase 1 已完成**：`openai_responses` 的 `delta-first terminal assembly` 已落地，`bwen` 这类 `delta 正常 + completed.output=[]` 场景不再被误判为失败。
- **Phase 2 已完成首轮收口**：`provider_interop_stream_support.py` 已拆成 `llm_stream_transport.py + llm_stream_events.py + facade`，且旧公开面兼容导出仍保留。
- **Phase 3 已完成第一版**：`interop_profile / capability profile` 已进入 `LLMConnection -> PreparedLLMHttpRequest -> stream runtime` 主链，本地 provider interop profile 也支持显式声明画像。
- **Phase 4 已完成第一版**：验证矩阵已覆盖 strict / delta-first / reasoning profile / probe profile 等关键场景，并通过 probe / verifier / assistant 联合回归。
- **目录标准化第一刀已完成**：LLM 兼容层真实实现已迁入 `shared/runtime/llm/` 与 `shared/runtime/llm/interop/`。
- **目录标准化第二刀已完成**：`mcp_client.py` 已迁入 `shared/runtime/mcp/`，`plugin_registry.py / plugin_providers.py` 已迁入 `shared/runtime/plugins/`。
- **内部导入收尾已完成**：仓库内部 `apps/api/app`、`apps/api/tests/unit`、`apps/api/scripts` 已不再直接导入旧根路径，而是全部改为真实子域路径。
- **最终收口已完成**：root compat shim 已删除，`shared/runtime` 根目录现在只保留跨子域基础件与 `__init__.py` 总入口。
- **Phase 5 当前结论已明确**：vendor-native dialect 继续保持“按需评估，不提前铺开 builder/parser/tests”，不作为本轮阻塞项。

当前实现真值以 shared/runtime 代码与对应单测为准；本方案文档保留为设计与实施记录。

---

## 1. 背景

easyStory 当前不是单一模型通道，而是要同时覆盖：

- OpenAI GPT
- Anthropic Claude
- Google Gemini
- Moonshot Kimi
- MiniMax
- Zhipu GLM
- DeepSeek
- Qwen 及各类 OpenAI-compatible 网关

当前项目已经有一套初步兼容层，核心入口在：

- 请求构造：[llm_protocol_requests.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/llm_protocol_requests.py)
- 非流式解析：[llm_protocol_responses.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/llm_protocol_responses.py)
- 流式解析 facade：[provider_interop_stream_support.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/interop/provider_interop_stream_support.py)
- assistant 统一调用入口：[llm_tool_provider.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/llm_tool_provider.py)
- provider interop 探测入口：[provider_interop_support.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/interop/provider_interop_support.py)
- 凭证验证入口：[verifier.py](/home/zl/code/easyStory/apps/api/app/modules/credential/infrastructure/verifier.py)

正式实现真值以下述子目录为准：

- `app/shared/runtime/llm/`
- `app/shared/runtime/llm/interop/`
- `app/shared/runtime/mcp/`
- `app/shared/runtime/plugins/`

`app/shared/runtime/` 根目录当前只保留真正跨子域基础件：

- `__init__.py`
- `errors.py`
- `tool_provider.py`
- `token_counter.py`
- `storage_paths.py`
- `template_renderer.py`

从规范文档看，当前正式支持的原生协议族只有 4 类：

- `openai_responses`
- `openai_chat_completions`
- `anthropic_messages`
- `gemini_generate_content`

这条口径已经写在：

- [model-provider-request-params-reference.md](/home/zl/code/easyStory/docs/specs/model-provider-request-params-reference.md)
- [model-provider-response-contract-reference.md](/home/zl/code/easyStory/docs/specs/model-provider-response-contract-reference.md)

也就是说，当前不是“完全没有中间层”，而是“已有兼容层，但还没有把同一协议族下的变体行为收口为稳定 contract”。

---

## 2. 直接触发原因

这次 `bwen` 渠道暴露出的现象，已经足够说明现有层次还不够稳：

1. `https://bwen.net/v1/responses` 与 `https://api.bwen.net/v1/responses` 都能返回 `HTTP 200`
2. 流式过程中持续返回了 `response.output_text.delta`
3. 但最终 `response.completed.response.output` 是空数组 `[]`
4. 当前本地 `openai_responses` 终态解析仍要求：
   - 要么 `output_text` 可直接提取
   - 要么 `output` 是非空列表
5. 于是本地在成功拿到流式文本后，仍然会在 completed 阶段抛：
   - `output must be a non-empty list`

这不是“上游没响应”，而是：

- **传输层成功**
- **流式增量成功**
- **终态收束失败**

这说明当前问题不在 assistant 业务层，而在**协议兼容中间层的终态装配 contract**。

---

## 3. 根因判断

### 3.1 当前抽象层次还不够细

当前实现主要是按 `api_dialect` 分支：

- `openai_responses`
- `openai_chat_completions`
- `anthropic_messages`
- `gemini_generate_content`

这比“按 provider 名写死一堆 if/else”已经好很多，但还不够。

因为真实世界里存在大量“同协议族、不同变体”的网关行为，例如：

- `openai_responses` 的流式 delta 正常，但 `response.completed.response.output=[]`
- `openai_chat_completions` 里有的网关会给 `reasoning_content`，有的不会
- 有的兼容层会把 usage 放在最终块，有的放在 `[DONE]` 前额外块
- 有的 `chat_completions` 支持 tools，但不支持 tool delta
- 有的 Gemini 兼容层返回 OpenAI 风格，不等于 Gemini 原生返回

因此，**只按 dialect 分支，不足以表达协议族内的行为差异**。

### 3.2 传输层、协议层、终态装配层还没有彻底分离

当前流式处理链已经有分层雏形，但还不完整：

- `iterate_stream_request()` 负责读 SSE
- `_extract_stream_delta()` 负责提取 delta
- `_extract_stream_terminal_response()` 直接把 terminal payload 交给统一 parser

问题就在这里：

- 终态 payload 的“合法性”和“最终文本如何收束”
- 目前仍然被绑死在 `parse_generation_response()` 的静态结构假设上

而 `bwen` 这类 Responses 变体已经证明：

- **终态响应不一定能单独重建文本**
- 但**delta 累积已经足够形成正确文本**
- 同时终态里又携带了 `usage / response_id / finish state`

所以这里需要单独的“终态装配层”，不能直接把 completed payload 当成标准非流式响应再 parse 一次。

### 3.3 assistant、provider interop probe、credential verifier 需要共享一套 contract

当前三条链路都已经复用同一批基础模块，这是对的：

- assistant 普通聊天 / tool-calling
- provider interop probe
- credential verifier

但也因此，只要兼容层 contract 不稳，同一个问题就会同时出现在：

- 助手页面真实聊天
- 凭证验证
- 本地 probe

这轮方案必须保证：**修的是共享中间层，不是给某个入口打补丁。**

### 3.4 当前测试矩阵缺少关键变体场景

当前已有测试已经覆盖不少正常路径：

- `openai_responses` 正常 non-stream parse
- `openai_responses` 正常 stream delta + completed
- `llm_tool_provider` 的 stream/non-stream 主链
- `credential verifier` 的 probe 主链

但这次真实暴露的关键变体还没有被明确固化成回归用例：

- `response.output_text.delta` 已产出有效文本
- `response.completed.response.output=[]`
- 最终应该成功收束为文本结果，而不是误报 `output must be a non-empty list`

因此，这次方案不能只写“修 `bwen`”，还必须把这类场景写入共享验证矩阵，防止后续在 parser 或 stream terminal 收束时再次回归。

---

## 4. 目标结果

本次中间层重构完成后，必须达到以下结果：

1. assistant 业务层不再直接承担厂商协议差异
2. provider interop、credential verifier、assistant runtime 共用同一套请求/流式/终态收束 contract
3. `openai_responses` 与 `openai_chat_completions` 明确分成两套协议族，不再混成“OpenAI 就一种”
4. 同一协议族下的网关差异通过“能力画像/变体 profile”表达，而不是把逻辑散落在业务层
5. GPT / Claude / Gemini / Kimi / MiniMax / GLM / DeepSeek / Qwen 的接入路径，都能被归入稳定的统一抽象
6. “请求能发出去”和“响应能正确解析”必须分开验证
7. 对于像 `bwen` 这种“delta 成功、completed 结构不标准”的网关，系统仍能正确收束结果，不再误报失败

---

## 5. 设计原则

### 5.1 不按 provider 名硬编码业务逻辑

业务层不能到处出现：

- `if provider == "gpt"`
- `if provider == "qwen"`
- `if provider == "deepseek"`

业务只应该消费统一归一化结果。

### 5.2 先区分协议族，再区分变体能力

第一层区分：

- `openai_responses`
- `openai_chat_completions`
- `anthropic_messages`
- `gemini_generate_content`

第二层区分：

- 该连接在这个协议族下的能力画像 / 兼容变体

### 5.3 传输层和协议层分离

必须明确拆开：

- **传输层**：HTTP / SSE 读流是否稳定
- **协议事件层**：怎么从 SSE 事件里抽 delta / stop / terminal payload
- **终态装配层**：如何把 delta + terminal metadata 收束成统一结果

### 5.4 请求映射和响应解析分开建模

保持与现有 spec 一致：

- 请求参数单独建模
- 响应契约单独建模
- 请求头 / client identity 单独建模

不要把它们重新揉成一个“大兼容类”。

### 5.5 失败必须显式暴露

不做静默 fallback，不做“解析失败就当普通文本成功”。

所有降级路径都必须是显式 contract，例如：

- 终态缺结构，但已有稳定 delta 文本，可走“delta-first terminal assembly”
- 终态 metadata 缺失，则只缺 metadata，不把整轮文本误报失败

---

## 6. 方案总览

本次方案不建议推翻现有结构，而是基于当前实现继续收口成五层。

### 6.1 第 0 层：连接配置层

保留现有 `LLMConnection` 的主骨架，但补充“协议变体画像”的概念。

当前保留字段：

- `api_dialect`
- `auth_strategy`
- `api_key_header_name`
- `base_url`
- `default_model`
- `extra_headers`

新增建议：

- `interop_profile` 或等价 runtime 内部画像字段

用途不是重新定义 provider，而是表达：

- `responses_strict`
- `responses_delta_first_terminal_empty_output`
- `chat_compat_plain`
- `chat_compat_reasoning_content`
- `chat_compat_usage_extra_chunk`

第一版不要求立刻落数据库列，也可以先在 runtime 通过探测/静态配置生成。

第一版策略需要明确写死：

- **热路径优先走声明式画像**
  - 来自 `api_dialect`
  - 来自 credential / profile 显式配置
  - 或来自 runtime 内部稳定映射
- **动态探测只用于诊断与互操作验证**
  - 用于 `provider_interop_check.py`
  - 用于人工定位连接兼容问题
  - 不进入 assistant / verifier 正式请求热路径
- **探测失败不会静默改写正式画像**
  - 不做“探测失败就自动换 profile”
  - 只显式输出证据，让配置或实现修正根因

### 6.2 第 1 层：语义请求模型

统一保留内部语义请求模型，例如现有 `LLMGenerateRequest`。

业务层只表达语义，不表达厂商字段名：

- `prompt`
- `system_prompt`
- `max_tokens`（内部语义名，后续映射）
- `tools`
- `response_format`
- `provider_continuation_state`

这里要继续坚持：

- assistant/runtime 不直接拼 `messages / input / contents`
- 也不直接决定 `max_output_tokens / max_tokens / generationConfig.maxOutputTokens`

### 6.3 第 2 层：协议族请求适配器

在现有 [llm_protocol_requests.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/llm_protocol_requests.py) 基础上继续稳定 4 个 builder：

- `openai_responses`
- `openai_chat_completions`
- `anthropic_messages`
- `gemini_generate_content`

同时把“协议族内变体差异”明确收口到 adapter config，而不是散落在业务层。

例如：

- `chat_completions` 家族里，是否允许 `reasoning_content`
- `responses` 家族里，是否要求 strict completed payload
- 某些 OpenAI-compatible 渠道是否需要禁用并行 tool calls

### 6.4 第 3 层：流式协议事件归一化器

在现有 [provider_interop_stream_support.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/interop/provider_interop_stream_support.py) 基础上拆成两部分责任：

1. **SSE reader**
   - 只负责稳定读取事件
   - 不负责理解 provider 语义

2. **protocol event normalizer**
   - 按协议族理解事件
   - 产出统一事件：
     - `delta_text`
     - `delta_reasoning`
     - `tool_call_delta`
     - `stop_reason`
     - `terminal_metadata`

这样：

- `response.output_text.delta`
- `choices[].delta.content`
- `content_block_delta`
- `candidates[].content.parts[].text`

都可以先变成统一的“增量事件”，再交给后面的终态装配层。

当前真实调用链也要写清楚，避免低估 Phase 2 的影响面：

- `iterate_stream_request()` 当前仍在 `provider_interop_stream_support.py`
- [llm_tool_provider.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/llm_tool_provider.py) 直接消费 `build_stream_probe_request() -> iterate_stream_request() -> build_stream_completion()`
- [verifier.py](/home/zl/code/easyStory/apps/api/app/modules/credential/infrastructure/verifier.py) 通过 `execute_stream_probe_request()` 复用同一条链
- `provider_interop_support.py` / `provider_interop_check.py` 也通过这套 shared runtime contract 工作

因此 Phase 2 的正确实施方式不是“一次性改掉所有调用方”，而是：

- 先在 shared runtime 内部拆出 `transport / events / terminal assembly`
- 外层暂时保留 `provider_interop_stream_support.py` 作为 facade
- 等 shared contract 稳定后，再决定是否继续收窄旧 facade

### 6.5 第 4 层：终态装配器

这是本次最关键的新层。

它负责把：

- 流式 delta 累积文本
- terminal payload
- usage
- provider_response_id
- tool calls
- finish status

装配成统一 `NormalizedLLMResponse`。

这里必须支持至少三种收束策略：

1. **strict-terminal**
   - 终态 payload 本身足够完整
   - 直接按终态重建结果

2. **delta-first**
   - 终态 payload 不含完整文本
   - 但 delta 已完整累计文本
   - 终态只补 `usage / response_id / finish state`

3. **terminal-only**
   - 流式没有 delta
   - 但终态 payload 里有完整文本或 output items

`bwen` 的 `responses` 流式，就属于典型的：

- `delta-first`

#### 6.5.1 `delta-first` 的边界合同

这部分必须显式，不允许“实现时自己猜”。

内容收束规则：

1. **strict-terminal**
   - terminal payload 自身能稳定重建文本
   - 最终 `content` 以 terminal 为准

2. **delta-first**
   - terminal 文本为空或不能稳定提取
   - 但 delta 累积文本非空
   - 最终 `content` 以 delta 累积结果为准

3. **terminal-only**
   - 没有可用 delta
   - terminal payload 自身能稳定提取文本
   - 最终 `content` 以 terminal 为准

冲突规则：

- 若 delta 文本与 terminal 文本都为空：显式失败
- 若 delta 文本非空、terminal 文本为空：允许 `delta-first`
- 若 delta 文本为空、terminal 文本非空：允许 `terminal-only`
- 若 delta 文本与 terminal 文本都非空且一致：按 terminal 收束，同时保留 terminal metadata
- 若 delta 文本与 terminal 文本都非空但不一致：**显式报协议不一致错误，不做静默择优**

metadata 规则：

- `finish_reason / usage / provider_response_id / provider_output_items` 优先取 terminal payload
- delta 链上的 `stop_reason` 只作为流式过程信号或诊断信息，不直接冒充最终 `finish_reason`
- Phase 1 不从原始 delta 事件反推复杂 `tool_calls`；若 terminal 缺少可解析 tool call，则显式暴露能力缺口

### 6.6 第 5 层：统一归一化结果

assistant、credential verifier、provider interop probe 只能消费统一结果：

- `content`
- `finish_reason`
- `input_tokens`
- `output_tokens`
- `total_tokens`
- `tool_calls`
- `provider_response_id`
- `provider_output_items`

业务层不再解析：

- `output[]`
- `choices[]`
- `content_block_*`
- `candidates[]`

---

## 7. 建议的模块化落点

不建议把当前文件全部推翻重写，而是按责任继续拆清。

建议目标结构：

```text
apps/api/app/shared/runtime/
  __init__.py
  errors.py
  tool_provider.py
  token_counter.py
  storage_paths.py
  template_renderer.py
  llm/
    __init__.py
    llm_protocol.py
    llm_protocol_types.py
    llm_protocol_requests.py
    llm_protocol_responses.py
    llm_endpoint_policy.py
    llm_stream_transport.py
    llm_stream_events.py
    llm_terminal_assembly.py
    llm_interop_profiles.py
    llm_tool_provider.py
    interop/
      provider_interop_support.py
      provider_interop_stream_support.py
      provider_interop_config_support.py
      gemini_probe_support.py
  mcp/
    __init__.py
    mcp_client.py
  plugins/
    __init__.py
    plugin_registry.py
    plugin_providers.py
```

建议职责：

- `tool_provider.py`
  - 保留为通用 `ToolProvider` 抽象
  - 不与 `llm_tool_provider.py` 合并
- `llm_protocol_requests.py`
  - 只做语义请求 -> 协议请求映射
- `llm_protocol_responses.py`
  - 只做非流式 payload -> normalized response
- `llm_endpoint_policy.py`
  - 只做模型端点与 base_url 规范化策略
- `llm_stream_transport.py`
  - 只做 SSE / HTTP 流读取
- `llm_stream_events.py`
  - 只做协议事件 -> 统一流式事件
- `llm_terminal_assembly.py`
  - 负责 delta + terminal payload 收束
- `llm_interop_profiles.py`
  - 维护协议族内能力画像 / 兼容变体
- `provider_interop_support.py`
  - 负责本地 probe profile 读取、override、rate limit 与 probe request 装配
- `provider_interop_config_support.py`
  - 负责 provider interop 本地 JSON 配置与 header/rate-limit 辅助解析
  - 它属于 `llm/interop/`，不是 `llm_interop_profiles.py` 本体
- `mcp_client.py`
  - 只承载 MCP tool call contract
- `plugin_registry.py` / `plugin_providers.py`
  - 属于通用 plugin/hook 执行子域
  - 不并入 `mcp/`，因为当前同时承载 `script / webhook / agent / mcp`

### 7.1 为什么不是简单拆成 `llm/ + mcp/`

当前 [plugin_providers.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/plugins/plugin_providers.py) 并不是纯 MCP 代码。它同时实现：

- `ScriptPluginProvider`
- `WebhookPluginProvider`
- `AgentPluginProvider`
- `McpPluginProvider`

而 [plugin_registry.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/plugins/plugin_registry.py) 也是通用注册器，不只服务 MCP。

因此如果把 `plugin_*` 直接塞进 `mcp/`，会重新制造“目录按名字看像 MCP，实际职责是通用 plugin runtime”的语义漂移。

### 7.2 当前真实文件边界要显式保留

这几条边界需要在目录迁移时保持不变：

- [tool_provider.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/tool_provider.py) 是抽象契约
- [llm_tool_provider.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/llm_tool_provider.py) 是 `ToolProvider` 的 LLM 实现
- [mcp_client.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/mcp/mcp_client.py) 是 MCP 调用 contract
- [plugin_registry.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/plugins/plugin_registry.py) / [plugin_providers.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/plugins/plugin_providers.py) 是 plugin runtime

目录迁移只能改变文件归属，不能把这些 contract 合并成新的“大而全运行时”。

### 7.3 文件体量控制

当前 `shared/runtime` 里已有几个明显超出舒适体量的高密度文件：

- [llm_protocol_requests.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/llm_protocol_requests.py)
- [llm_protocol_responses.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/llm_protocol_responses.py)
- [provider_interop_stream_support.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/interop/provider_interop_stream_support.py)
- [llm_tool_provider.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/llm_tool_provider.py)

因此目录标准化不能只做“搬文件不拆职责”。后续实施时要遵守两条：

- 先按子域迁移：`llm/`、`mcp/`、`plugins/`
- 再在子域内继续拆职责，避免把 `800+` 行文件原样搬进新目录

现有 [provider_interop_stream_support.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/interop/provider_interop_stream_support.py) 最终应被拆薄，不再同时承担：

- HTTP 读流
- 协议事件解析
- 终态收束
- 错误消息拼装

拆分后的直接受影响调用方主要有：

- [llm_tool_provider.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/llm_tool_provider.py)
- [provider_interop_support.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/interop/provider_interop_support.py)
- [verifier.py](/home/zl/code/easyStory/apps/api/app/modules/credential/infrastructure/verifier.py)

assistant 业务层原则上不直接受影响，因为它只应该继续消费 shared runtime 的统一 contract。

---

## 8. 分阶段实施顺序

### Phase 1. 先修正 `openai_responses` 终态装配 contract

目标：

- 修掉 `bwen` 这类“delta 成功、completed.output=[]”却误报失败的问题

最小改动：

- 保留现有 dialect 分层
- 新增终态装配 helper
- `openai_responses` 流式 completed 不再强依赖非空 `output`
- 若已有 delta 文本，则允许以 delta 文本为最终 content，并从 completed 中抽取 usage / response_id / finish state
- 若 delta 与 terminal 都有文本但不一致，则显式报协议不一致
- `finish_reason` 仍优先取 terminal，不从最后一个 delta 事件静默推导最终结果
- 第一刀不引入“按场景分 parser”，仍然保持 assistant / verifier / probe 共用 shared runtime contract

这一步只解决**当前已复现问题**，不扩大协议面。

### Phase 2. 抽出统一流式事件层

目标：

- 把 `provider_interop_stream_support.py` 从“大而全”拆成 transport + protocol event normalizer

结果：

- assistant / verifier / probe 共用同一条流式事件链
- 后续再补新方言时，不需要反复改 transport 代码

### Phase 3. 引入 interop profile / capability profile

目标：

- 在相同 `api_dialect` 下表达不同网关/厂商变体能力

结果：

- 不再把“同是 chat-completions / responses，但行为不同”的差异硬编码到散乱分支里
- 第一版优先采用声明式画像，不把在线探测变成正式热路径依赖

### Phase 4. 补齐验证矩阵

目标：

- 把“请求能发出去”和“响应能正确解析”彻底拆开验证

至少覆盖：

- `openai_responses` strict terminal
- `openai_responses` delta-first terminal-empty-output
- `openai_chat_completions` plain
- `openai_chat_completions` with reasoning_content
- `anthropic_messages`
- `gemini_generate_content`

### Phase 5. 再评估 vendor-native dialect

这一步不作为当前阻塞项。

像：

- Kimi 原生
- MiniMax 原生
- GLM 原生
- DeepSeek 原生

只有在确实需要 vendor-native 能力时，才新增独立 builder / parser / tests，不提前空铺。

---

## 9. 结果定义

方案落地后，验收结果必须是：

1. GPT 走 `responses` 时，标准 OpenAI 与 `bwen` 这类变体都能稳定收束
2. Qwen / Kimi / GLM / DeepSeek / MiniMax 等 OpenAI-compatible 渠道，至少能稳定落在 `chat_completions` 家族 contract 上
3. Claude 与 Gemini 原生链路不受本次改造副作用影响
4. assistant 页面、credential verifier、provider interop probe 对同一连接的成功/失败判断一致
5. assistant 业务层不再出现 provider-specific 解析逻辑
6. 新增厂商或网关时，优先补 profile / parser / tests，而不是在业务层打补丁

---

## 10. 验证矩阵

本次方案实施时，至少要补下面几类测试。

### 10.1 非流式解析

- `openai_responses`：`output_text`
- `openai_responses`：`output[]`
- `openai_chat_completions`：`choices[].message.content`
- `anthropic_messages`
- `gemini_generate_content`

### 10.2 流式解析

- `openai_responses`：delta + completed.output[]
- `openai_responses`：delta + completed.output=[]
- `openai_responses`：无 delta，仅 completed.output[]
- `openai_chat_completions`：普通文本 delta
- `openai_chat_completions`：`reasoning_content` 变体
- `anthropic_messages`：message event 链
- `gemini_generate_content`：native SSE

### 10.3 共享入口一致性

- assistant 普通聊天
- assistant tool-calling
- credential verifier
- provider interop probe

同一连接、同一协议族下，四者应共享同一成功/失败结论。

### 10.4 Backward Compatibility

除了新增变体用例，还必须守住当前已成立的正常路径：

- `llm_protocol_responses.py` 现有 non-stream parser 行为不回归
- `provider_interop_stream_support.py` 现有正常 `openai_responses` / `openai_chat_completions` / `anthropic_messages` / `gemini_generate_content` stream 用例继续通过
- `llm_tool_provider.py` 的 `execute()` / `execute_stream()` 正常成功路径继续通过
- `credential verifier` 的成功、空内容失败、HTTP 错误映射、stream 协议错误路径继续通过

其中至少要显式补上这类回归场景：

- `openai_responses`：delta 正常 + terminal `output=[]` + metadata 完整
- `openai_responses`：delta 文本与 terminal 文本冲突，显式报协议不一致
- `credential verifier`、`provider interop probe`、`assistant stream` 对同一变体得出一致结论

---

## 11. 不纳入本方案的事项

- 立即给所有厂商上 vendor-native dialect
- 在 assistant 业务层临时对单个 provider 写补丁
- 通过静默 fallback 掩盖协议不匹配
- 把请求参数、响应解析、请求头策略重新揉成一个“大兼容 God Object”

---

## 12. 当前建议

如果按正确性和收益排序，建议实施顺序是：

1. 先修 `openai_responses` 的终态装配 contract，明确支持 `delta-first terminal assembly`
2. 再拆流式事件层
3. 再补 interop profile / capability profile
4. 最后再考虑 vendor-native dialect 的扩张

这样可以先把当前 `bwen` / assistant 页面读文件的真实阻塞问题解掉，同时不把整个兼容层做成一次性大重写。
