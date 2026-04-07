# Assistant 原生 Tool-Calling Runtime 设计

| 字段 | 内容 |
|---|---|
| 文档类型 | 功能设计 |
| 文档状态 | 生效 |
| 创建时间 | 2026-04-04 |
| 更新时间 | 2026-04-07 |
| 关联文档 | [20-assistant-runtime-chat-mode](./20-assistant-runtime-chat-mode.md)、[21-assistant-project-document-tools](./21-assistant-project-document-tools.md)、[16-mcp-architecture](./16-mcp-architecture.md)、[系统架构设计](../specs/architecture.md) |

---

> 本文档当前仍是 assistant runtime 中原生 tool-calling 的正式设计真值。
>
> 若你在跟踪本轮文档重构路线、待迁移章节或阶段状态，请看 [Assistant Runtime 文档重构计划](../plans/2026-04-07-assistant-runtime-doc-refactor.md)。未明确回写到本文的目标语义，不视为正式真值。

## 1. 目的

定义 easyStory ordinary chat 的原生 tool-calling runtime，使后续接入项目文稿工具、外部无状态工具、更多 provider 方言、显式审批与恢复协议时，不需要反复改 `AssistantService` 主骨架。

本文只解决 ordinary chat runtime 本身：

- tool loop 属于哪一层
- provider 方言如何适配
- run / step 真值如何持久化
- continuation state 如何设计
- SSE / 取消 / 幂等 / 预算如何收口
- 授权、审批与写入策略如何划界

项目文稿工具域、统一目录、`document_ref`、版本与 revision 约束，统一见 [21-assistant-project-document-tools](./21-assistant-project-document-tools.md)。

---

## 2. 当前代码基线

当前代码基线已经进入 `v1A` 的最小闭环：

- request contract 已正式包含 `conversation_id + client_turn_id + continuation_anchor + document_context + requested_write_scope + requested_write_targets`
- `AssistantService` 主链已分叉为普通单轮调用与 `AssistantToolLoop`
- `ToolProvider` 仍承担共享 LLM 调用器职责，不拥有本地 `project.*` 执行权
- `AssistantTurnRun / AssistantToolStep`、`provider_continuation_state`、`pending_tool_calls_snapshot`、`state_version` 已有正式持久化真值
- Hook / MCP / Plugin 仍主要服务 hook 事件，不是 ordinary chat 的旁路工具循环
- SSE 已补 `run_started / tool_call_start / tool_call_result / completed`
- `document_context` 已有结构化 request contract，Studio 旧 prompt stuffing 只剩兼容投影层

当前仍未完全闭合的边界主要是：

- session 级 approval / resume 协议
- 更完整的 context compaction 审计
- 更丰富的 SSE 事件族与恢复协议

---

## 3. 设计目标

本方案要求：

1. ordinary chat 的 tool-calling 是主 runtime 的正式扩展，不是 Hook / MCP 旁路
2. provider 兼容差异被收口到共享模型 transport 层，不泄漏到业务层
3. tool loop 有独立 run / step 真值，可恢复、可去重、可审计
4. 项目内工具执行权始终掌握在 easyStory 本地 runtime 手里
5. 授权、审批、写入、取消、预算、流式事件都以 runtime 为中心
6. 后续增强优先扩 descriptor / executor / project document domain，不反复改 `AssistantService`

本方案不追求：

- `v1A` 就实现真正的 session 级恢复
- `v1A` 就开放大量外部工具和并行 tool call
- 把 provider 的 server-side tool loop 当成 easyStory 项目工具的执行入口

---

## 4. 长期硬边界

### 4.1 tool-calling 是 ordinary chat runtime 的正式扩展

ordinary chat 主链长期必须是：

1. 装配规则、历史、当前消息、结构化 turn context
2. 调用模型，允许返回文本或工具调用 item
3. 若返回工具调用，执行本地 tool loop
4. 把工具结果回填到同一 run 的 continuation state
5. 继续推理，直到拿到最终回复

禁止把这条链路挂到：

- Hook 插件执行链
- MCP 插件旁路
- provider 兼容层里的隐式工具循环

### 4.2 `project.*` 工具始终由本地 runtime 执行

`AssistantModelToolCapabilities` 可以表达 provider 是否支持 server-side tools，但不能把 easyStory 项目内工具的执行权交出去。

长期约束：

- `project.*` 工具始终由 easyStory 本地 runtime 执行
- provider server-side tools 只适合后续接入外部、无状态、低信任耦合工具
- 项目内文稿读写不得绕过本地授权、版本、revision、审计和幂等模型

### 4.3 provider 兼容层属于共享基础设施，不属于 assistant 私有域

当前代码里，provider 兼容职责仍主要落在 `shared/runtime`，而不是 assistant 私有层。

当前实际分层是：

- `shared/runtime`
  - `LLMToolProvider`
  - `llm_protocol_*` 请求准备 / 响应归一化函数
  - continuation support / capability 描述
- `assistant/service`
  - `AssistantService`
  - `AssistantToolLoop`
  - `AssistantToolDescriptorRegistry`
  - `AssistantToolExposurePolicy`
  - `AssistantToolExecutor`
  - `AssistantTurnRunStore`
  - `AssistantToolStepStore`

这条边界的意义仍然不变：workflow / incubator / verifier 继续复用同一套 provider transport 与方言语义，不会反向复制 assistant 私有实现。

### 4.4 项目文稿能力主归属 `project` 域，`content` 只提供 canonical 适配

assistant 只拥有：

- tool loop
- run / step
- SSE / 取消 / 审批协议
- tool descriptor / exposure / executor glue

assistant 不拥有：

- 项目文稿统一目录真值
- 文稿 identity / version / revision 规则
- canonical 文稿读写规则
- 文件层文稿版本与审计真值

主归属约束直接定死为：

- `project`
  - 拥有统一目录、`path -> document_ref`、`resource_uri`、`catalog_version`
  - 拥有文件层文稿 version / revision / audit 真值
  - 对 assistant 暴露统一项目文稿能力入口
- `content`
  - 只通过公开 service 提供总大纲 / 开篇设计 / 章节等 canonical 文稿读取适配
  - 不拥有统一目录真值，不反向拥有 assistant tool executor

assistant 只依赖 `project` 暴露的统一项目文稿能力，不直接同时编排 `project` 与 `content` 两套平行文稿入口。

### 4.5 内部输出不能退化成“文本 + tool_calls[]”

对外响应第一阶段仍可保持“最终文本为主”，但 runtime 内核必须先统一成 item 级模型。

建议最小 `AssistantOutputItem[]` 语义：

- `text`
- `tool_call`
- `tool_result`
- `reasoning`
- `refusal`

`AssistantOutputItem` 至少还应能稳定表达：

- `item_type`
- `item_id`
- `status`
- `provider_ref`
- `call_id`
- `payload`

其中：

- `tool_call`
  - `payload` 至少要能承载 `tool_name + normalized_arguments`
- `tool_result`
  - `payload` 至少要能承载 `AssistantToolResultEnvelope`
- `text`
  - 若存在中间 commentary / final answer 分层，应通过显式 `phase` 或等价字段区分
- `reasoning`
  - 可以保留 provider-specific opaque payload，但不能只保留纯文本摘要

`usage` 与 `finish_reason` 不应继续混进 item taxonomy：

- `usage`
  - 属于 response / run 级元数据
- `finish_reason`
  - 属于 response / run 级终态元数据
- 若需要正式对象
  - 应单独落到 `AssistantOutputMeta` 或等价 response metadata 结构

原因：

- OpenAI Responses 更接近 output items / `call_id` / `function_call_output`
- Anthropic tool use 是 content blocks / `tool_use` / `tool_result`
- streamed tool arguments 可能出现 partial / invalid JSON 片段
- 后续若要做 reasoning roundtrip、审批恢复、trace 展示，不应再重做输出层

---

## 5. 目标架构

### 5.1 分层总览

```text
Entry(SSE/HTTP)
  -> AssistantService
    -> AssistantTurnRunStore
    -> AssistantToolDescriptorRegistry
    -> AssistantToolExposurePolicy
      -> AssistantToolPolicyResolver
    -> AssistantToolLoop
      -> LLMToolProvider(shared/runtime)
      -> AssistantToolExecutor
        -> ProjectDocumentCapabilityService(project)
    -> AssistantToolStepStore
```

### 5.2 对象职责

- `AssistantService`
  - 负责 turn / run 生命周期、事件流、取消、恢复入口
  - 不直接判断文稿可写性，不直接落业务写入
- `AssistantToolLoop`
  - 负责 item 解析、工具循环、结果回填、继续推理
  - 不直接判断 provider 名称，也不直接拼 OpenAI / Anthropic 方言参数
- `AssistantToolDescriptorRegistry`
  - 维护工具正式合同真值
- `AssistantToolExposurePolicy`
  - 当前直接基于 descriptor registry、turn context 与 policy resolver 决定本轮实际暴露哪些工具
  - 当前仓库里尚未独立拆出 `AssistantToolCatalogAssembler`
- `AssistantToolPolicyResolver`
  - 负责把授权、预算、模型能力、审批恢复与作用域约束收敛成稳定 policy 决策
- `AssistantToolExecutor`
  - 只负责按 `tool_name + execution_locus` 路由到本地项目工具或后续外部工具执行器
  - 不负责决定本轮暴露哪些工具
- `shared/runtime` 模型层
  - 只做 provider transport、请求映射、响应归一化、能力描述
- `project` 文稿能力层
  - 作为统一项目文稿能力主归属
  - 负责目录、identity、读取、写入、版本、revision、catalog
- `content`
  - 只提供 canonical 文稿公开读取能力

### 5.3 Hook 生命周期

进入原生 tool-calling runtime 后，现有 assistant hooks 不能继续默认绑定为“每次 continuation 都触发一次”。

长期口径直接定为：

- 现有 `before_assistant_response`
  - 是 run 级生命周期事件
  - 每个 run 只触发一次，在首个模型请求前执行
- 现有 `after_assistant_response`
  - 是 run 级生命周期事件
  - 每个 run 只触发一次，在最终 assistant 输出确定后执行
- 现有 `on_error`
  - 只在 terminal run failure 时触发一次
  - 不对可恢复的 tool retry、provider retry、continuation retry 逐次触发

若后续需要细粒度可观测或自动化编排，应新增显式 step 级事件，例如：

- `tool_call_started`
- `tool_call_completed`
- `tool_call_failed`
- `before_model_continue`

这些事件与现有 run 级 hooks 分层存在；不得把 run 级 hooks 复用成 step 级多次触发器。

若后续需要真正的工具级 hook，正式建议另起：

- `pre_tool_use`
- `post_tool_use`

它们应绑定 `tool_call_id / descriptor snapshot / tool result envelope`，而不是继续复用 run 级 hook payload。

### 5.3A Hook 术语分层

为避免后续继续把“用户自动化能力”和“runtime 内核事件”混成一层，本文口径直接定为：

- 当前产品里用户可配置的 `HookConfig`
  - 统称 `Assistant Automation Hook` 或“用户自动化 Hook”
  - 负责在 `before_assistant_response / after_assistant_response / on_error` 这类产品事件上挂接自动化动作
- ordinary chat runtime 内核里的 run / step / tool 生命周期
  - 统称 `Lifecycle Event`
  - 不等同于用户 Hook
- 若后文提 `pre_tool_use / post_tool_use`
  - 指 runtime lifecycle event name
  - 不是当前 `HookConfig` 直接复用的事件名

实现层即使短期还沿用 existing naming，也不改变这层语义分层。

---

## 6. 运行时真值

### 6.1 `AssistantTurnRun`

`AuditLog` 和 `PromptReplay` 不是 ordinary chat tool loop 的恢复真值。

建议新增 `AssistantTurnRun`，至少包含：

- `run_id`
- `conversation_id`
- `owner_id`
- `project_id`
- `client_turn_id`
- `continuation_anchor_snapshot`
- `requested_write_scope`
- `requested_write_targets_snapshot`
- `granted_write_scope`
- `tool_catalog_version`
- `exposed_tool_names_snapshot`
- `resolved_tool_descriptor_snapshot`
- `turn_context_hash`
- `runtime_claim_snapshot`
- `state_version`
- `status`
- `finish_reason`

其中 `tool_catalog_version` 在当前 `v1A` 的实际口径已收口为“本轮最终可见 descriptor 快照版本”。

- 这个字段已经进入 run snapshot / exposure context / stale run 恢复链
- 它不再借用 `document_context.catalog_version`
- 它当前仍不是独立 discovery phase 或 catalog assembler 的产物；是否存在隐藏候选工具，仍由 `DescriptorRegistry + ExposurePolicy` 决定
- `cancel_state`
- `budget_snapshot`
- `provider_continuation_state`
- `normalized_input_items_snapshot`
- `pending_tool_calls_snapshot`
- `started_at`
- `updated_at`
- `completed_at`

其中：

- `conversation_id`
  - 作为普通聊天产品会话锚点
  - 用于聚合同一会话下的 turn / run / trace
  - 不等同于 session 级 write grant 真值
- `client_turn_id`
  - 默认只要求在同一 `conversation_id` 内稳定唯一
  - 服务端幂等映射不得丢掉 `conversation_id` 维度
- `continuation_anchor_snapshot`
  - 保存本轮声明的前序 run / transcript 锚点
  - request contract 仍允许只传 `previous_run_id`；但 `v1A` 当前冻结到 run snapshot 时，至少应归一化为 `previous_run_id + messages_digest`
  - 若请求未显式提供 `messages_digest`，runtime 也必须把实际校验过的 direct-parent digest 冻结进去
  - 在没有 server-side conversation truth 时，冲突检测只能基于这层显式锚点，而不是 `conversation_id` 本身
- `requested_write_targets_snapshot`
  - 冻结本轮可成为候选写目标的显式请求集合
  - 恢复时不得重新从 `selected_document_refs` 或 UI 本地状态猜测
- `resolved_tool_descriptor_snapshot`
  - 保存本轮实际暴露给模型的 descriptor 快照
  - 不能只冻结工具名，否则 schema、approval policy、timeout 变化后会导致恢复与审批重放漂移
- `provider_continuation_state`
  - 用于衔接 provider continuation 能力
  - 类型应为 provider 无关的 opaque object，而不是只保存一个字符串 id
  - 若某 provider 不支持 continuation，也必须有等价 transcript replay 锚点
- `state_version`
  - 每次 run 状态变化单调递增
  - SSE、审批恢复、取消与去重都基于它判断时序
- `runtime_claim_snapshot`
  - `v1A` 可记录本地 runtime 的 `host / pid / instance_id`
  - 只用于识别“旧进程已中断导致的残留 running run”，不是 session 级恢复真值
  - 未确认旧进程已结束前，不得把 `running` run 静默当成可重放状态
- `normalized_input_items_snapshot`
  - 保存继续推理所需的归一化输入快照
  - 不依赖“重新拼原始 prompt 文本”恢复
- `compaction_snapshot`
  - 保存首轮历史压缩的触发原因、前后 token 估算、压缩/保留消息数量、受保护文稿路径与摘要
  - 只记录 runtime 输入压缩，不改写 transcript 真值
- `continuation_compaction_snapshot`
  - 保存最近一次 tool loop continuation request budget compaction 的审计结果
  - 当前至少记录 `phase=tool_loop_continuation`、`level=soft|hard`、前后 token 估算、受影响 item 数量与裁剪统计
  - 与首轮 `compaction_snapshot` 分离，避免把消息历史压缩和 continuation 投影压缩混成一份真值
- `continuation_request_snapshot`
  - 保存最近一次真正发送给模型的 continuation request projection
  - 当前至少记录 `continuation_items` 与 `provider_continuation_state`
  - `continuation_items` 允许为空列表；空列表仍表示 latest request view，而不是缺失值
  - 与 `provider_continuation_state`、`continuation_compaction_snapshot` 分离，避免把 provider 基态、request 投影和压缩审计混成一份真值
- `pending_tool_calls_snapshot`
  - 为审批、恢复和中断后收口提供稳定真值

### 6.2 `AssistantToolStep`

建议新增 `AssistantToolStep`，至少包含：

- `tool_call_id`
- `run_id`
- `step_index`
- `tool_name`
- `descriptor_hash`
- `normalized_arguments_snapshot`
- `arguments_hash`
- `target_document_refs`
- `approval_state`
- `approval_grant_id`
- `status`
- `dedupe_key`
- `idempotency_key`
- `result_summary`
- `result_hash`
- `error_code`
- `started_at`
- `completed_at`

长期建议：

- `approval_state` 至少支持 `not_required | pending | approved | rejected | expired`
- `status` 至少支持 `queued | reading | validating | writing | committed | completed | failed | cancelled`
- `v1A` 当前实现会记录 `approval_state in {not_required, pending, approved}`
  - `pending` 仅表示 grant-bound 写工具缺少有效 grant，当前还没有正式 `approval_request` 对象
- 审批、恢复、幂等必须绑定 `descriptor_hash + arguments_hash`，不能只按 `tool_name` 复用历史结论

### 6.2A `AssistantApprovalRequest`

`approval_state` 与 `approval_grant_id` 还不够表达完整审批语义。

建议新增 `AssistantApprovalRequest`，至少包含：

- `approval_request_id`
- `run_id`
- `tool_call_id`
- `descriptor_hash`
- `arguments_hash`
- `target_document_refs`
- `subject_summary`
- `requested_at`
- `expires_at`
- `status`
- `resolved_at`
- `resolved_by`
- `decision_reason`

语义分层必须固定为：

- `approval_request`
  - 是“待决策对象”
  - 回答“当前到底在等用户/系统批准什么”
- `approval_grant`
  - 是“批准后签发的可执行能力凭证”
  - 回答“哪些工具 / 目标文稿 / 版本约束在当前 run 中可继续执行”

进一步约束：

- 同一个 `approval_request` 最多解析出一个有效 `approval_grant`
- `approval_grant` 过期不等于 `approval_request` 消失；二者不得复用同一个 id
- `AssistantToolStep.approval_grant_id` 只引用 grant，不替代 request 本身
- `v1A` 当前尚未落正式 `approval_request / resume` 协议
  - `always_confirm` descriptor 继续隐藏
  - run store / SSE / resume 现阶段还不携带 `approval_request` 实体
  - 本节保持为 `v1B+` 设计目标，不得误读为已实现能力

### 6.3 幂等优先于自动重试

第一阶段必须明确：

- 每个前端 turn 请求携带稳定 `client_turn_id`
- 服务端建立 `(owner_id, project_id, conversation_id, client_turn_id) -> run_id` 映射
- 每个工具步骤生成稳定 `tool_call_id`
- 写入幂等键至少绑定 `run_id + tool_call_id + document_ref`

执行语义：

- 同一个幂等写请求重复到达时，返回第一次成功结果
- 不允许因为重试而重复制造 revision
- 自动重试只适用于只读操作，或尚未提交的写前阶段
- 一旦写入已提交，恢复必须走“读最新状态后继续”，而不是盲写第二次
- 对“旧进程已中断”的残留 `running` run，`v1A` 可以显式终止为失败态，避免同一 `client_turn_id` 永久卡在 `run_in_progress`
- 即使识别出 stale run，也不得静默重放整轮 turn；终止并显式暴露错误优先于盲目自动重试

---

## 7. 结构化 turn context

ordinary chat 不能继续把“当前文稿路径、截断正文、额外参考路径”硬拼进用户消息正文作为正式运行时真值。

建议第一阶段就把输入正式收口为：

- `conversation_id`
  - 普通聊天当前会话的稳定锚点
- `continuation_anchor`
  - 当前请求预期承接的前序 run / transcript 锚点
- `messages`
  - 只保留真实会话消息
- `document_context`
  - 文稿相关结构化输入
- `requested_write_scope`
  - 当前 turn 请求的写权限范围
- `requested_write_targets`
  - 当前 turn 显式允许成为候选写目标的文稿集合
  - `v1A` request 形状固定为 `document_ref[]`
- `input_data`
  - 仅保留为现有 Skill / Hook / Agent 的兼容扩展袋

同时应明确当前两层输入真值：

- `system_prompt + prompt`
  - 面向当前 provider 请求文本投影
- `NormalizedInputItem[]`
  - 面向 run snapshot、continuation 与 provider replay

若后续引入 `PromptSection[]`，它也只能是新的装配投影层，不得反向取代 `NormalizedInputItem[]` 的恢复真值职责。

### 7.0A `NormalizedInputItem[]` 最小类型集

`NormalizedInputItem[]` 不应只作为“若干 prompt 片段”的别名。

`v1A` 至少应能表达以下 item 类型：

- `message`
  - 保存真实 transcript item
  - 至少包含 `role=user|assistant`、`content` 与可选 `phase`
- `rule`
  - 保存用户规则、项目规则与平台安全基线等长期约束
- `skill_instruction`
  - 保存 Skill / Agent 显式注入的任务模板语义
- `hook_selection`
  - 保存本轮显式启用的 hook 集合
- `model_selection`
  - 保存本轮实际解析后的模型选择 / 覆写结果
- `document_context`
  - 保存 request projection 的 flat 文稿上下文
- `document_context_binding`
  - 保存归一化后的 `DocumentContextBinding[]` 或等价 binding item
- `tool_call`
  - 保存 `tool_call_id / tool_name / normalized_arguments`
- `tool_result`
  - 保存 `tool_call_id / AssistantToolResultEnvelope`
- `reasoning`
  - 保存可 replay 的 reasoning item 或 provider opaque continuation payload
- `refusal`
  - 保存模型拒绝项
- `compacted_context`
  - 保存 compaction 的衍生产物

规则：

- `message` 的顺序就是 transcript 顺序，不得被 compaction 原地改写
- `当前用户消息` 若在 runtime 内被单独引用，只能是 `messages` 末条 `user` 业务消息的派生视图，不是第二份 request 真值
- `tool_result` 必须通过 `tool_call_id` 绑定到明确的 `tool_call`
- `compacted_context` 是衍生 item，不是对原始 transcript 的覆盖
- `NormalizedInputItem[]` 才是 replay 真值；当前请求的真实装配投影仍是 `system_prompt + prompt`

`document_context` 最少包含：

- `active_path`
- `active_document_ref`
- `active_binding_version`
- `selected_paths`
- `selected_document_refs`
- `active_buffer_state`
- `catalog_version`

后续可增补：

- `context_bindings`
- `catalog_snapshot`
- `active_buffer_excerpt`
- `exposed_tool_names`
- `write_target_hints`

规则：

- `messages` 只保留当前会话里的 `user / assistant`
- `conversation_id` 独立于 `messages` 存在；即使迁移期仍由前端显式传完整消息，也不能继续只靠前端本地 active conversation state 作为唯一锚点
- `continuation_anchor` 最少建议包含 `previous_run_id` 与可选 `messages_digest`
- `v1A` 采用 request snapshot truth：`messages` 是本轮 transcript 真值，`conversation_id` 只负责产品会话归属
- `v1A` 当前回合的“当前会话历史”默认就等于 request 中提供的 `messages` snapshot，而不是服务端另读出的隐藏 transcript
- 在正式 conversation store 落地前，runtime 不得凭 `conversation_id` 静默回填 request 之外的隐藏历史
- 若产品层存在 conversation store、turn 持久化或会话切换索引，它们也只是下一轮装配或 UI 恢复的候选来源，不得在当前 `AssistantTurnRun` 创建后反向改写本轮 snapshot truth
- 若请求提供 `continuation_anchor`，runtime 必须校验它与 `conversation_id`、`messages` 的 direct-parent 关系；失败返回 `conversation_state_mismatch`
- 当请求提供 `continuation_anchor` 但省略 `messages_digest` 时，runtime 当前仍必须基于 `messages[:-1]` 计算 direct-parent digest，并把它写入 `continuation_anchor_snapshot`
- 若请求未提供 `continuation_anchor`，runtime 只能把该请求视作该 `conversation_id` 下的新分支或无锚点请求，不得宣称已完成跨请求冲突检测
- Studio 旧的 prompt stuffing 只允许短期兼容，不再作为正式真值
- `document_context` 是新的正式系统字段；`input_data` 不再承载系统级文稿上下文真值
- `document_context` 一旦进入 runtime，必须先完成 `path -> document_ref + binding_version` 归一化并落入 run snapshot，不能把路径级上下文直接拿去签发写入 grant
- flat `document_context` 只是 request projection；runtime 内部正式真值应尽快归一化成 `DocumentContextBinding[]`
- `requested_write_scope` 只回答“本轮有没有写能力”；`requested_write_targets` 只回答“哪些文稿可成为候选写目标”
- `selected_document_refs` 只是读取/参考集合，不得隐式升级成写入白名单
- 若 `requested_write_targets` 缺失，`v1A` 默认只把 `active_document_ref` 视为候选写目标
- `v1A` 实际只接受“缺失”或“仅包含 `active_document_ref` 的单元素 `document_ref[]`”；若显式传入其他目标，必须返回显式错误
- `v1A` 保留 `input_data`，只作为兼容扩展袋，不直接废弃
- Hook payload 在迁移期同时暴露 `request.input_data` 与 `request.document_context`
- 老 Skill / Hook 若仍依赖 `input_data`，在 `v1A` 继续可运行；新增系统语义一律写入正式字段
- `v1A` 只有 `active_document_ref` 允许成为实际写目标，因此 dirty buffer 拒签先只绑定 `active_buffer_state`
- 若当前来源文稿或潜在写回目标存在 dirty buffer，则 runtime 不签发写入 grant；后续若要支持多目标写入，必须先为每个候选目标引入独立 buffer 快照
- 与本轮读写无关的其他 dirty buffer，不应一刀切阻塞整个 turn

`document_context` 的长期三层映射应固定为：

1. request projection
   - Studio / API 透传的 flat `document_context`
2. runtime normalized binding
   - ordinary chat runtime 内部冻结到 `AssistantTurnRun` 的 `DocumentContextBinding[]`
3. project binding
   - `project` 文稿能力层正式消费的 `ProjectDocumentContextBinding`

字段映射至少应固定为：

- `document_context.active_document_ref -> DocumentContextBinding.document_ref -> ProjectDocumentContextBinding.document_ref`
- `document_context.active_binding_version -> DocumentContextBinding.binding_version -> ProjectDocumentContextBinding.binding_version`
- `document_context.active_buffer_state.dirty -> DocumentContextBinding.buffer_dirty`
- `document_context.active_buffer_state.base_version -> DocumentContextBinding.base_version -> ProjectDocumentContextBinding.base_version`
- `document_context.active_buffer_state.buffer_hash -> DocumentContextBinding.buffer_hash -> ProjectDocumentContextBinding.buffer_hash`
- `document_context.active_buffer_state.source -> DocumentContextBinding.buffer_source -> ProjectDocumentContextBinding.buffer_source`
- `document_context.catalog_version -> DocumentContextBinding.catalog_version -> ProjectDocumentContextBinding.catalog_version`

`active_buffer_state` 最少建议包含：

- `dirty`
- `base_version`
- `buffer_hash`
- `source`

`v1A` 下“可信 active buffer snapshot” 的最小判定必须固定为：

- `dirty = false`
- `base_version` 非空
- `buffer_hash` 非空，且执行时仍命中当前持久化文稿内容
- `source = studio_editor`
- 上述字段必须进入 normalized binding，并进一步绑定到 write grant snapshot，不能只停留在 flat `document_context`

### 7.1 `active_buffer_state` 的前后端数据通道

这层状态不能由 runtime 事后猜测，也不能依赖服务端重新读取持久化文稿替代前端缓冲区。

`v1A` 正式口径：

- Studio 在发起 turn request 时，若当前存在活动编辑器，必须把该时刻的 `active_buffer_state` 一并透传
- `active_buffer_state` 代表“用户当前本地缓冲区快照”，不是“服务端持久化内容状态”
- runtime 只消费 request 中冻结下来的快照，不反向读取前端本地状态，也不在 run 过程中二次查询编辑器
- 若 `active_path / active_document_ref` 对应的文稿可能成为本轮写入目标，但 request 缺少可信 `active_buffer_state`，则该文稿不得获得写入 grant
- `v1A` 不对非 active 文稿推断 buffer 状态；若后续要允许非 active 目标写入，必须新增按 `document_ref` 分桶的 buffer state 集合
- 若当前没有活动编辑器，应显式留空，而不是伪造 `dirty=false`

迁移要求：

- 旧的 prompt stuffing 可以继续短期兼容文稿内容提示
- 但 `active_buffer_state` 必须通过正式 request contract 透传，不能继续藏在 prompt 文本或 `input_data` 非正式字段里

---

## 8. 工具定义、暴露与执行

### 8.1 `AssistantToolDescriptorRegistry`

工具定义必须集中为正式合同，不允许在执行器里临时拼 schema。

建议 descriptor 至少包含：

- `name`
- `description`
- `input_schema`
- `output_schema`
- `origin`
- `trust_class`
- `plane`
- `mutability`
- `execution_locus`
- `approval_mode`
- `idempotency_class`
- `timeout_seconds`

其中 `execution_locus` 必须是稳定的一等字段，而不是 provider adapter 内部枚举：

- `local_runtime`
  - 由 easyStory 自身 runtime 在本地进程内执行
  - `project.*` 在 `v1A` 固定属于该类
- `provider_hosted`
  - 由模型提供方托管执行的内建工具能力
- `remote_mcp`
  - 由远端 MCP server 提供并经 runtime 转接的工具能力

### 8.2 `AssistantToolExposurePolicy`

该层当前实际接收并冻结的上下文字段包括：

- 当前 turn context
- granted write scope
- tool catalog version
- 当前轮实际可承载的 schema / result token 预算
- 文稿目录状态
- 模型能力
- 当前 budget snapshot
- runtime 是否支持审批恢复协议

但 `v1A` 当前真正命中可见性判断的主条件只有：

- 是否处于 `project_id` 作用域内
- `descriptor.approval_mode`
- `requested_write_scope`
- `requested_write_targets`
- `active_document_ref / active_binding_version`
- `active_buffer_state` 是否是可信快照
- active `document_context_binding` 是否 `writable=true`

也就是说：

- `tool_catalog_version`
- `budget_snapshot`
- `model_capabilities`
- `runtime_supports_approval_resume`

这些字段当前已经进入 exposure context，但还不是 `v1A` 的主过滤条件。

其中 `tool_catalog_version` 当前由本轮最终可见 descriptor 集合稳定派生，不再复用项目文稿目录版本。

长期 `approval_mode` 枚举当前仍保持：

- `none`
- `grant_bound`
- `always_confirm`

但 `v1A` 实际暴露规则必须是：

- 只暴露 `approval_mode in {none, grant_bound}` 的工具
- `always_confirm` descriptor 可以存在，但不得对模型暴露

当前 `v1A` 的实际暴露规则是：

- 所有 `project.*` 工具都先经过 `AssistantToolDescriptorRegistry`
- 若不在项目作用域内，全部 `project.*` 工具隐藏，原因是 `not_in_project_scope`
- `approval_mode=always_confirm` 的工具一律隐藏，原因是 `unsupported_approval_mode`
- `project.write_document` 只有在当前 turn 已拿到 `grant_bound` 写入前提时才可见；否则隐藏，原因是 `write_grant_unavailable`
- 当前可见工具集合因此稳定收口为：
  - 只读场景：`project.list_documents / project.search_documents / project.read_documents`
  - 可写场景：在只读三件套基础上额外暴露 `project.write_document`

#### 当前 Tool Governance 合同

- `AssistantToolDescriptorRegistry`
  - 维护当前工具合同真值
  - 当前 descriptor 字段正式以代码为准：
    - `name`
    - `description`
    - `input_schema`
    - `output_schema`
    - `origin`
    - `trust_class`
    - `plane`
    - `mutability`
    - `execution_locus`
    - `approval_mode`
    - `idempotency_class`
    - `timeout_seconds`
- `AssistantToolExposurePolicy`
  - 当前直接遍历 registry 内的 descriptor，并结合 turn context 收口本轮真正可见集合
- `AssistantToolPolicyResolver`
  - 当前负责把项目作用域、approval mode、grant-bound 写入前提收敛成单轮 policy 决策
- `AssistantToolExecutor`
  - 负责按 `tool_name + execution_locus` 执行，不反向决定暴露与否

当前仓库里还没有独立的 `AssistantToolCatalogAssembler`。如果后续工具族真的扩张到需要显式候选池阶段，应该新建独立对象，而不是继续把发现逻辑塞进 `ExposurePolicy`；但这不属于当前已落地真值。

#### 当前 Discovery Contract

当前实际合同是：

- `project.search_documents`
  - 是项目文稿候选发现工具
  - 不是“搜索有哪些工具可用”的通用工具发现入口
- 当前没有 first-class `search_tools` / `ToolSearch` 工具
- 当前也没有独立的 runtime 内部 discovery phase；“哪些工具可见”就是 registry + exposure/policy 的结果
- ordinary chat 里的项目范围启发式提示仍然存在于 prompt 文本层，但它不等于工具发现协议，也不等于工具可见性真值

#### `AssistantToolPolicyResolver`

`AssistantToolExposurePolicy` 之前，还需要一层稳定 policy resolver，避免后续把“工具是否可见”“本轮是否自动批准”“是否允许命中某些目标文稿”混成一个 if-else 大杂烩。

建议最小输入：

- descriptor snapshot
- `origin / trust_class`
- 当前 owner / project 作用域
- 用户层 / 项目层工具策略
- `requested_write_scope / granted_write_scope`
- runtime 当前是否支持审批恢复

建议最小输出：

- `visibility`
  - `hidden | visible`
- `effective_approval_mode`
  - `none | grant_bound | always_confirm`
- `allowed_target_document_refs`
- `redaction_policy`
  - 是否允许在 trace / SSE 中回显输入与输出摘要

长期优先级建议：

1. managed / system deny
2. 当前 turn 的显式授权与运行时硬限制
3. 项目层策略
4. 用户层策略
5. descriptor 默认值

合并规则必须再收死为：

- `visibility` 取逐层收窄，不取并集；任一层显式 deny、缺失必要 grant、或命中 runtime 硬阻塞时，结果直接为 `hidden`
- 对写工具与其他 mutation 能力，`requested_write_scope=disabled`、grant 缺失、dirty buffer 阻塞、恢复协议缺失等前置条件失败，项目策略和用户策略都不得重新放宽
- prompt / rule 语义里仍可保持“项目规则比用户规则更具体”，但 tool policy 不复用这条覆盖链；危险能力授权属于独立安全决策
- 若项目层与用户层都允许可见，则 `effective_approval_mode` 取更严格者，再与 descriptor 默认值比较后取最终更严格结果
- `allowed_target_document_refs` 只能逐层收窄，不得由较低信任层扩张
- 任何会影响 trace / SSE 回显的 `redaction_policy` 也只允许逐层收紧

其中 `project.*` 在 `v1A` 的默认口径应固定为：

- `origin=project_document`
- `trust_class=local_first_party`
- 写工具仍需额外命中 `grant_bound` 与 `DocumentMutationPolicy`

### 8.3 `AssistantToolExecutor`

该层只负责：

- 根据 `tool_name + execution_locus` 路由工具执行
- 调用 `project` 暴露的统一项目文稿能力或后续外部工具服务
- 产出统一 `AssistantToolResultEnvelope`

该层不负责：

- 动态拼 schema
- 决定本轮工具暴露集合
- 自己维护文稿真值

### 8.4 `AssistantToolResultEnvelope`

统一结果 envelope 至少包含：

- `tool_call_id`
- `status`
- `structured_output`
- `content_items`
- `resource_links`
- `error`
- `audit`

序列化口径必须固定：

- 顶层正式真值只保留 `tool_call_id / status / structured_output / content_items / resource_links / error / audit`
- 若为兼容当前 UI 需要提供 `display_text`，它只能是 `content_items` 的 projection，不得单独承载业务语义
- 工具业务字段一律进入 `structured_output`
- `truncated / next_cursor` 等继续读取语义属于 `structured_output`；`content_items` 只是给模型与 UI 的文本投影
- 若后续 tool loop 请求超出输入预算，runtime 当前只允许在 continuation request projection 上裁剪大文本或清空与 `structured_output` 重复的 `content_items`；正式 envelope 真值不因此改写
- SSE、tool trace、run / step 持久化都只消费同一套 envelope 语义
- `audit` 当前只作为审计扩展袋；字段形状仍以实际执行器输出为准，暂未在 `v1A` 统一成更细的 canonical schema

---

## 9. provider 能力协商与 continuation

### 9.1 共享能力矩阵

`AssistantModelToolCapabilities` 最小建议覆盖：

- `strict_tool_schema`
- `parallel_tool_calls`
- `allowed_tools_filter`
- `tool_choice_modes`
- `streamed_tool_arguments`
- `reasoning_items_roundtrip`
- `server_side_tool_loop`
- `continuation_mode`

### 9.2 request / response 适配必须成对存在

当前 shared/runtime 已经通过成对的请求准备与响应归一化吸收 provider 差异：

- request 侧
  - 负责把 assistant runtime 输入投影成具体 provider 请求
- response 侧
  - 负责把 provider 响应折回统一输出语义

`AssistantToolLoop` 不直接判断 provider 名称，也不直接拼 OpenAI / Anthropic 参数。

### 9.2.1 现有 `ToolProvider` 的迁移口径

当前仓库已经存在 `ToolProvider / LLMToolProvider`。

当前 ordinary chat 主链的真实口径是：

- `LLMToolProvider`
  - 仍是 ordinary chat 主链实际使用的共享 LLM 调用器
  - 负责 provider request 准备、流式调用与响应归一化
- `ToolProvider`
  - 仍是 assistant 当前模型调用抽象

若后续真要引入专门的 `AssistantModelClient`，那是一次真实代码重构，不应提前在本文写成已生效现状。

### 9.2.2 当前 provider 请求投影

当前 provider 请求的正式输入投影仍然是：

- `system_prompt`
- `prompt`
- `tools`
- `continuation_items`
- `provider_continuation_state`

对应当前实现：

- runtime 先生成 `system_prompt + prompt`
- `LLMToolProvider` 再把这组输入投影到具体 provider 方言
- run store 持久化与 continuation 真值落在 `NormalizedInputItem[]`
- `PromptSection[]` 尚未成为当前代码里的正式源模型

因此当前正式边界是：

- provider 角色差异仍由共享 runtime adapter 吸收
- `system_prompt + prompt` 是当前真实投影，不应在文档里假装已经被 `PromptSection[]` 替代
- 若后续真的引入 `PromptSection[]`，必须在代码与测试落地后再回写本文

### 9.3 continuation state 必须正式建模

要支持审批、取消后继续、去重和稳定 trace，run 真值里必须保留 continuation 锚点，而不是只保存最终文本。

长期至少支持两种 continuation 模式：

1. `provider_continuation`
   - 由 provider continuation state 衔接后续推理
   - 允许保存 `response_id`、reasoning items、approval cursor、已导入工具列表等 provider-specific 信息
2. `runtime_replay`
   - runtime 根据已归一化 items 重新装配继续推理所需输入

同时应为 provider 能力显式建模：

- `continuation_mode`
  - `provider_continuation | runtime_replay | hybrid`
- `tolerates_interleaved_tool_results`
  - 表示中间插入本地 tool result 后，provider continuation 是否仍有效
- `requires_full_replay_after_local_tools`
  - 表示一旦本地执行工具并回填结果，就必须退回 runtime replay

选择规则：

- 若 provider 不支持 continuation，直接走 `runtime_replay`
- 若 provider 支持 continuation 但不接受 interleaved local tool results，则在工具结果回填后切到 `runtime_replay`
- 只有 provider continuation 能覆盖“本地工具结果已插入后继续推理”时，runtime 才可继续复用 `provider_continuation_state`

即使 `v1A` 只先落最小闭环，也必须先把这层字段设计好，避免后续又改 run store。

### 9.4 `v1A` 明确关闭并行 tool call

`v1A` 规则：

- provider 侧并行 tool call 关闭
- runtime 串行执行工具
- streamed tool arguments 可以被 normalizer 接受
- 但前端不要求直接展示参数增量
- 串行执行还能保持 `binding_version / base_version / active_buffer_state` 校验链稳定，避免多写目标并行时在同一 run 内制造版本基准漂移

---

## 10. 授权、审批、预算与取消

### 10.1 `v1A` 只接受 `disabled | turn`

在没有真实 session 真值前，`requested_write_scope` 只接受：

- `disabled`
- `turn`

若 UI 想保留“当前会话允许更新”的产品心智，可先作为前端本地偏好；后端真实授权直到具备 session 锚点前，都只签发 turn 级 grant。

`requested_write_scope` 与 `requested_write_targets` 必须配套理解：

- `requested_write_scope`
  - 定义本轮是否允许生成写入 grant
- `requested_write_targets`
  - 定义 grant 最多可以覆盖哪些候选目标
  - `v1A` request 形状固定为 `document_ref[]`
- `selected_document_refs`
  - 只是参考集合，不是写入目标集合
- `v1A` 只接受“缺失”或“仅包含 `active_document_ref` 的单元素集合”

### 10.1A 审批对象与 grant 关系

审批与 grant 不得再只靠“一个 state 字段”承载全部语义。

正式关系应为：

1. `AssistantToolPolicyResolver`
   - 先决定本轮 descriptor 是否可见，以及其 `effective_approval_mode`
2. 若命中 `always_confirm`
   - 生成 `AssistantApprovalRequest`
   - 等待 `approval_required -> approval_resolved`
3. 若审批通过
   - 再签发 `approval_grant`
4. tool step 真正执行时
   - 只消费 grant，不直接消费 request

这样可以保证：

- 待决策对象、已批准能力、实际执行步骤三者分层
- 后续暂停 / 恢复 / 过期 / 重新审批不会挤压到 `AssistantToolStep` 一个对象里
- `grant_bound` 与 `always_confirm` 能共用同一套 run / SSE / audit 骨架

### 10.2 grant 与 mutation policy 分层

不要把所有判断都揉进一个对象。

建议拆成：

- `AssistantToolPolicyResolver`
  - 回答“这个工具在本轮是否对模型可见，以及采用哪种批准模式”
- `DocumentWriteGrantResolver`
  - 回答“本轮有没有写权限”
- `DocumentMutationPolicy`
  - 回答“这个文稿现在能不能写，以及为什么”

grant 结构建议至少预留：

- `grant_id`
- `allowed_tool_names`
- `target_document_refs`
- `binding_version_constraints`
- `base_version_constraints`
- `expires_at`
- `approval_mode_snapshot`

### 10.3 `RunBudget`

第一阶段就应把预算设计成正式协议。

建议最小字段：

- `max_steps`
- `max_tool_calls`
- `max_input_tokens`
- `max_history_tokens`
- `max_tool_schema_tokens`
- `max_tool_result_tokens_per_step`
- `max_read_bytes`
- `max_write_bytes`
- `max_parallel_tool_calls`
- `tool_timeout_seconds`

预算超限必须显式失败，不做静默 fallback。

当前 `v1A` 的预算口径还应明确为：

- 若 provider 能提供 `context_window_tokens`，则 `max_input_tokens` 当前按 `context_window_tokens - max_output_tokens` 收口；无法解析窗口时允许留空
- 输入估算当前使用本地 `TokenCounter`，分别统计 `system_prompt`、当前 prompt projection、tool schema 的 JSON 投影、continuation projection 的 JSON 投影，再求和
- 若 provider continuation 走 `latest_items` 复用路径，则估算时不重复计入 `prompt` 文本，而改用 `provider_continuation_state.latest_items`

### 10.4 Tool Loop 错误恢复语义

tool loop 进入多步执行后，错误不能再只有一个笼统的 `error`。

第一阶段就应把错误恢复语义分成三类：

1. `return_error_to_model`
   - 适用于读取失败、参数校验失败、只读工具超时、`version_conflict / invalid_json / schema_validation_failed / write_target_mismatch` 这类模型可在同一轮修正的错误
   - runtime 把错误封装成失败的 `tool_result envelope` 回填给模型
   - 由模型决定是否换路径、缩小范围、重新读取或结束回答
2. `terminal_run_failure`
   - 适用于权限拒绝、写入 grant 失效、`active_buffer_state_required / dirty_buffer_conflict`、预算耗尽、恢复协议缺失、显式取消后不可继续
   - runtime 直接终止 run，向前端返回明确失败原因
   - 不把这类错误伪装成“工具已返回错误，请模型自行处理”
3. `bounded_retry_before_commit`
   - 只适用于提交前的短暂基础设施错误，例如网络瞬断、provider 短暂不可用、只读阶段超时
   - 必须有显式重试上限
   - 一旦进入 `writing / committed` 边界，不允许隐式重试写入

长期规则：

- `tool_loop_exhausted`、`budget_exhausted`、`unsupported_approval_mode` 一律属于 `terminal_run_failure`
- 写入一旦提交成功，恢复必须走“读取最新状态后继续”，不得盲写第二次
- 权限、预算、dirty buffer、catalog/version 冲突都必须完整暴露，不能静默降级成“本轮跳过写入”

### 10.4A 正常结束与 runtime 硬终止边界

ordinary chat 的正常结束条件必须继续保持为：

- 模型返回了最终回复
- 当前响应中不再包含新的 tool call

这意味着：

- “工具命中为空”“读取结果为空”“搜索无结果”“返回 `truncated=true + next_cursor`”都不是 runtime 自行结束 run 的理由
- 只要工具执行成功产出了正式 envelope，后续是否继续读取、是否换工具、是否直接回答，都应交回模型决定

与此同时，runtime 仍保留硬终止权：

- 预算耗尽
- 取消命中不可安全中断的边界
- 并行 tool call 超出当前能力
- 授权 / 安全 / dirty buffer / version 冲突命中硬阻塞
- 状态持久化失败或其他运行时不变量破坏

因此长期原则应明确为：

- 模型决定正常路径上的“继续推理还是完成回答”
- runtime 决定所有越过安全、预算、恢复与执行边界的硬失败
- executor 产出空结果不等于 loop 结束；只有“无更多 tool call 的模型回复”才是正常完成

### 10.5 Context Compaction 与预算触发

长会话下，runtime 必须允许显式的 context compaction；否则小说创作场景会稳定撞上上下文膨胀问题。

当前 `v1A` 已落地的预算收口路径有两类：

- 首轮触发点发生在首个模型调用前的 prompt 组装阶段
- 首轮触发条件是按 `system_prompt + prompt + tools` 估算后超过 `max_input_tokens`
- 首轮只压缩 request snapshot 里的较早历史消息
- 进入 tool loop 后，runtime 还会在每次继续调用模型前，对 continuation request projection 应用同一 `max_input_tokens` 预算收口
- continuation 预算收口只作用于回填给模型的 projection；不会改写 transcript、原始 tool result envelope 或已持久化 step 结果
- 当前用户消息不会被首轮历史 compaction 压缩

当前输出规则是：

- compaction 成功时，运行时会生成早期历史摘要，并保留最近一段历史消息
- `AssistantTurnRun.compaction_snapshot` 当前记录首轮历史 compaction
- `AssistantTurnRun.continuation_request_snapshot` 当前记录最近一次真正发给模型的 continuation request projection；若 continuation 语义允许空投影，则 `continuation_items=[]` 也是合法真值
- `AssistantTurnRun.continuation_compaction_snapshot` 当前记录最近一次 tool loop continuation projection 的预算收口
- 该 snapshot 当前已显式包含 `phase=initial_prompt` 与 `level=soft|hard`
- compaction 改的是 runtime 输入视图，不改 `messages` transcript 真值，也不改持久化会话历史
- 同一摘要会进入 `NormalizedInputItem(item_type=compacted_context)`
- tool loop continuation 预算收口当前会先收窄 `project.read_documents / project.search_documents / project.list_documents` 的 bulky `structured_output` 投影，再裁剪最大文本槽；若 `structured_output` 已完整存在且仍超限，可清空冗余 `content_items`
- continuation request snapshot 若存在 compaction，应冻结压缩后的 latest request view，而不是压缩前的原始 continuation projection
- 当前 continuation compaction snapshot 只保留 latest snapshot，不记录多次 budget compaction 的完整历史
- 若任一阶段 compaction 或 continuation 预算收口后仍超限，应显式返回 `budget_exhausted`，而不是继续偷偷裁剪

分级 compaction、context collapse、恢复注入与更完整的 continuation compaction 历史审计，目前都还不属于已落地真值。

### 10.6 取消语义

`should_stop` 不能只服务“文本流是否停止”。

建议最小执行状态：

- `reading`
- `validating`
- `writing`
- `committed`

规则：

- 用户点击停止时，先记录 `cancel_requested`
- `AssistantToolLoop` 在 step 边界、继续推理前、工具执行前检查取消信号
- 若取消发生在 `reading / validating`，可直接终止
- 若取消发生在 `writing`，必须等待当前提交成功或失败后再结束
- 若取消发生在 `committed` 之后，终态必须明确告诉前端“本轮已停止，但已有写入生效”

---

## 11. SSE 协议

ordinary chat 一旦进入 tool loop，SSE 不能再只有文本 delta。

建议所有事件都带：

- `run_id`
- `event_seq`
- `state_version`
- `ts`

`v1A` 最小事件集：

- `run_started`
- `chunk`
- `tool_call_start`
- `tool_call_result`
- `completed`
- `error`

`v1B` 再补：

- `approval_required`
- `approval_resolved`
- `context_compacted`
- `budget_warning`
- 更完整的 trace / budget / cancel 事件

事件要求：

- `run_started` 必须首帧发出
- `tool_call_start` 至少带 `tool_call_id`、`tool_name`、目标摘要
  - `project.read_documents` 至少带 `paths`
  - `project.write_document` 至少带 `path`、`base_version`
  - `project.search_documents` 至少带 `query` 或 `path_prefix`，以及已生效的检索过滤摘要
- `tool_call_result` 至少带成功/失败状态、结果摘要、必要时的 `document_revision_id` 与 `run_audit_id`
- `approval_required` 至少带 `approval_request_id`、`tool_call_id`、`subject_summary`、`expires_at`
- `approval_resolved` 至少带 `approval_request_id`、`status`、必要时的 `grant_id`

---

## 12. 实施落点

建议直接在现有结构上收口，不新起平行大层：

- `apps/api/app/modules/assistant/service/`
  - `assistant_service.py`
  - `assistant_execution_support.py`
  - `assistant_run_budget.py`
  - `assistant_runtime_terminal.py`
  - `agents/`
    - `assistant_agent_dto.py`
    - `assistant_agent_file_store.py`
    - `assistant_agent_service.py`
    - `assistant_agent_support.py`
  - `context/`
    - `assistant_context_compaction_support.py`
    - `assistant_document_context_support.py`
    - `assistant_prompt_render_support.py`
    - `assistant_prompt_support.py`
    - `assistant_input_budget_support.py`
  - `hooks/`
    - `assistant_hook_dto.py`
    - `assistant_hook_file_store.py`
    - `assistant_hook_service.py`
    - `assistant_user_hook_support.py`
  - `hooks_runtime/`
    - `assistant_hook_support.py`
    - `assistant_hook_runtime_support.py`
    - `assistant_hook_providers.py`
  - `mcp/`
    - `assistant_mcp_dto.py`
    - `assistant_mcp_file_store.py`
    - `assistant_mcp_service.py`
    - `assistant_user_mcp_support.py`
  - `preferences/`
    - `preferences_dto.py`
    - `preferences_service.py`
    - `preferences_support.py`
  - `rules/`
    - `assistant_rule_dto.py`
    - `assistant_rule_service.py`
    - `assistant_rule_support.py`
  - `skills/`
    - `assistant_skill_dto.py`
    - `assistant_skill_file_store.py`
    - `assistant_skill_service.py`
    - `assistant_skill_support.py`
  - `turn/`
    - `assistant_turn_prepare_support.py`
    - `assistant_turn_llm_bridge_support.py`
    - `assistant_turn_run_store.py`
    - `assistant_turn_run_support.py`
    - `assistant_turn_runtime_support.py`
  - `tooling/`
    - `assistant_tool_registry.py`
    - `assistant_tool_catalog_support.py`
    - `assistant_tool_policy_resolver.py`
    - `assistant_tool_exposure_policy.py`
    - `assistant_tool_executor.py`
    - `assistant_tool_loop.py`
    - `assistant_tool_runtime_dto.py`
    - `assistant_tool_step_store.py`
- `apps/api/app/shared/runtime/`
  - `llm_tool_provider.py`
  - `llm_protocol_requests.py`
  - `llm_protocol_responses.py`
  - `llm_protocol_types.py`
- `apps/api/app/modules/project/` 与 `apps/api/app/modules/content/`
  - `project` 提供统一项目文稿能力主入口
  - `content` 提供 canonical 文稿公开读取适配

边界长期保持：

- `AssistantService`
  - 负责 run 生命周期，不直接落业务写入
- `AssistantToolLoop`
  - 负责工具循环、继续推理、取消/审批收口
- `shared/runtime`
  - 不承载 assistant run 状态和业务工具循环
- `project`
  - 不承载 tool loop，只承载统一项目文稿正式能力
- `content`
  - 不承载 tool loop，只承载 canonical 文稿公开读取能力

---

## 13. 分阶段实施

### 13.1 `v1A`

`v1A` 最小闭环建议为：

1. 引入 item 级内部归一化模型
2. 请求 DTO 增加 `conversation_id + client_turn_id + continuation_anchor`
3. 请求输入正式收口到 `conversation_id + continuation_anchor + messages + document_context + requested_write_scope + requested_write_targets + input_data(兼容袋) + execution selectors(agent_id / skill_id / hook_ids) + model selection / override`
4. 新增 `AssistantTurnRun / AssistantToolStep`
5. 新增 `state_version / provider_continuation_state / pending_tool_calls_snapshot`
6. 引入 `AssistantToolDescriptorRegistry + AssistantToolExposurePolicy + AssistantToolExecutor`
7. 引入 `AssistantToolPolicyResolver`
8. 引入 `AssistantToolLoop`
9. 引入 `RunBudget`
10. SSE 至少补 `run_started / tool_call_start / tool_call_result`
11. `requested_write_scope` 在 `v1A` 只接受 `disabled | turn`
12. `v1A` 只暴露 `approval_mode in {none, grant_bound}` 的工具
13. 现有 hooks 在 `v1A` 明确为 run 级事件，不按每次 continuation 重复触发
14. Hook payload 在 `v1A` 同时暴露 `request.input_data` 与 `request.document_context`
15. Studio 旧 prompt stuffing 降为兼容层，不再作为正式运行时真值
16. 当前请求装配仍以 `system_prompt + prompt` 投影给 provider；run snapshot / continuation 真值收口为 `NormalizedInputItem[]`
17. `active_buffer_state` 与 `binding_version` 通过正式 request contract / 归一化 binding 透传，不再依赖 prompt stuffing
18. tool loop 错误恢复语义显式区分 `return_error_to_model / terminal_run_failure / bounded_retry_before_commit`

### 13.2 `v1B`

`v1B` 再补：

1. richer SSE 事件
2. `approval_required / approval_resolved`
3. 基于 `run_id + tool_call_id` 的恢复协议
4. `tool_catalog_version / descriptor_hash / turn_context_hash` 的更完整校验
5. 完整 `catalog_snapshot` 与 `catalog_version` 校验
6. 更完整的 tool trace 回执
7. 若 assistant runtime 拿到真实 session 真值，再评估 session 级 write grant
8. context compaction、`context_compacted` 事件与更细的压缩审计
9. `pre_tool_use / post_tool_use` 等真正的 tool 级 hooks

### 13.3 `v1A` 边界总表

为避免约束分散在多节里，`v1A` 最终边界统一收口为：

| 主题 | `v1A` 固定口径 |
|---|---|
| 会话真值 | `messages` 是 transcript snapshot truth；`conversation_id` 只负责产品会话归属 |
| 当前用户消息 | 若 runtime 内部单独引用，只能由 `messages` 末条 `user` 业务消息派生，不是第二份 request 真值 |
| continuation | 只接受显式 `continuation_anchor` 做 direct-parent 校验；缺失时视作新分支/无锚点请求 |
| turn 输入 | 正式收口到 `conversation_id + continuation_anchor + messages + document_context + requested_write_scope + requested_write_targets + input_data(兼容袋) + execution selectors(agent_id / skill_id / hook_ids) + model selection / override` |
| 幂等 scope | `(owner_id, project_id, conversation_id, client_turn_id) -> run_id`；不得丢掉 `conversation_id` 维度 |
| 文稿上下文 | request projection 进入 runtime 后，必须归一化成 `DocumentContextBinding[]`；项目文稿层消费 `ProjectDocumentContextBinding` |
| 写权限 | 真实后端授权只支持 `disabled | turn`，不做假的 session grant |
| 写目标 | `requested_write_targets` 的 `v1A` request 形状固定为 `document_ref[]`；缺失时默认仅 `active_document_ref`，且 `v1A` 不接受其他非 active 目标 |
| 版本锚点 | `catalog_version` 只管 discovery freshness；mutation 必须依赖独立 `binding_version + base_version` |
| provider continuation | 仅在 provider 能接受 interleaved local tool results 时继续复用；否则退回 `runtime_replay` |
| tool loop | 本地 runtime 串行执行；provider 并行 tool call 关闭 |
| tool descriptor | 必须显式包含 `execution_locus`；执行器按 `tool_name + execution_locus` 路由，而不是只按名字 |
| approval | `approval_request` 是待决策对象，`approval_grant` 是已批准能力凭证；二者不得混同 |
| compaction | 不改写 `messages` 真值；当前用户消息、当前 `document_context`、当前 grant 约束、待审批/待提交结果、待继续读取结果不得首轮压缩 |
| hooks | 现有 hooks 仍是 run 级事件，不因 continuation/tool loop 重复触发成 step 级多次事件 |
| Prompt 真值 | 当前 provider 输入投影仍是 `system_prompt + prompt`；恢复与审批真值落在 `NormalizedInputItem[]` |

---

## 14. 硬约束

以下约束必须长期保持：

1. assistant tool-calling 必须是 ordinary chat runtime 的正式扩展，而不是 Hook / MCP 旁路
2. provider capability 只是能力描述，不直接决定业务执行权
3. `project.*` 工具必须由本地 runtime 执行，不能下放给 provider server-side tool loop
4. provider transport / dialect adapter 属于共享基础设施，不属于 assistant 私有域
5. 项目文稿目录、identity、版本、revision 主归属 `project` 域；`content` 只提供 canonical 适配
6. 输出归一化不能只停在“文本 + tool_calls[]”，内部必须保留 item / block 语义
7. `AssistantTurnRun / AssistantToolStep` 与通用审计 / 回放必须职责分离
8. `v1A` 不做假的 session 级授权真值
9. 在没有正式恢复协议前，不得把 `approval_mode=always_confirm` 的工具暴露给模型
10. 在结构化 `document_context` 落地后，Studio 旧 prompt stuffing 不得继续作为并行真值长期保留
11. `conversation_id` 与 `run_id` 必须分离；前者归属产品会话，后者归属 turn 级执行
12. `当前用户消息` 若在 runtime 内部被单独引用，也只能是 `messages` 末条 `user` 业务消息的派生视图，不得并行引入第二份 request 真值
13. 在正式 conversation store 落地前，不得基于 `conversation_id` 静默补全 request 外历史消息
14. run 幂等映射默认必须包含 `conversation_id`；除非 `client_turn_id` 另有正式全局唯一协议，否则不得只按 `(owner_id, project_id, client_turn_id)` 去重
15. 现有 run 级 hooks 不得因 tool loop/continuation 被重复触发成 step 级多次事件
16. context compaction 不得原地改写 `messages` transcript 真值
17. `v1A` 的 `requested_write_targets` 只能是 `document_ref[]`，且不得把非 active 目标静默放入写入集合
18. 活动文稿缺失可信 `active_buffer_state` 时，不得对其签发写入 grant；这里的“可信”最少要求 `dirty=false + base_version + buffer_hash + source=studio_editor`，且这些字段必须进入 grant snapshot；非 active 目标若没有独立 buffer 快照，也不得在 `v1A` 获得写入 grant
19. 权限、预算、dirty buffer、恢复协议缺失等错误不得被静默降级成“模型可自行忽略”的普通工具错误
20. `selected_document_refs` 不能隐式扩成写入白名单
21. `catalog_version` 不能单独承担 mutation binding；单文稿写入必须有独立 `binding_version`
22. 即便后续引入 `PromptSection`，它也不能作为恢复与审批唯一真值；需要 replay 的系统语义必须进入 `NormalizedInputItem[]`
23. `project.read_documents` 只面向统一项目目录，不得退化成任意文件系统读取
24. tool descriptor 必须显式包含 `execution_locus`；执行器不得只按 `tool_name` 做长期路由
25. `approval_request` 与 `approval_grant` 必须分层；pending decision 不得只靠 `approval_state` 隐含表达

---

## 15. 结论

这轮改造的本质不是“给 assistant 多接几个工具”，而是把 ordinary chat 正式升级成一个具备以下能力的原生 runtime：

- 本地受控 tool loop
- 共享 provider 适配层
- run / step 真值
- continuation state
- 结构化 turn context
- 明确授权、预算、取消与审批语义

只有这层先立住，后面的项目文稿工具、外部搜索工具和更多 provider 能力，才不会继续把主运行时拖回补丁式扩展。
