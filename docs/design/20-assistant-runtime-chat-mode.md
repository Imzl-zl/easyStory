# Assistant 运行时与聊天主路径

| 字段 | 内容 |
|---|---|
| 文档类型 | 功能设计 |
| 文档状态 | 生效 |
| 创建时间 | 2026-04-03 |
| 更新时间 | 2026-04-07 |
| 关联文档 | [22-assistant-tool-calling-runtime](./22-assistant-tool-calling-runtime.md)、[21-assistant-project-document-tools](./21-assistant-project-document-tools.md)、[16-mcp-architecture](./16-mcp-architecture.md)、[系统架构设计](../specs/architecture.md) |

---

> 本文档当前仍是 assistant runtime 的正式设计真值。
>
> 若你需要查看 2026-04-07 这轮 assistant runtime 收口的历史实施过程，请看 [Assistant Runtime 文档重构计划](../plans/2026-04-07-assistant-runtime-doc-refactor.md)。当前正式语义以本文、相关 design 文档与代码为准。

## 1. 目的

定义 easyStory 当前 assistant 主路径的正式口径，避免再把“规则”“Skill”“Agent”“MCP”混成一层。

当前目标不是复刻编程型 CLI 的全部能力，而是收口出适合小说创作的默认聊天模式：

- 没有任何额外配置时，也必须能直接聊天
- 规则是长期自动增强
- Skill / Agent 是显式增强，不是启动条件
- MCP 是能力层，不是每轮都注入的 prompt 文本

本文只负责定义 assistant 主路径的语义、分层和默认装配边界。

- ordinary chat 的原生 tool-calling runtime、tool loop、run/step 真值、SSE 事件语义，统一见 [22-assistant-tool-calling-runtime](./22-assistant-tool-calling-runtime.md)
- 项目文稿工具域、统一目录、`document_ref`、版本与 revision 约束，统一见 [21-assistant-project-document-tools](./21-assistant-project-document-tools.md)

---

## 2. 设计原则

### 2.1 默认可用

普通聊天不能依赖 `skill_id` 或 `agent_id`。

用户只要满足以下条件，就应能直接开始对话：

- 当前会话存在消息
- 已有可执行模型连接

### 2.2 用户规则优先于产品预设

普通创作聊天默认不使用产品内置写作 prompt，不注入系统内置创作人设。

产品只负责装配：

- 当前会话历史
- 当前用户消息
- 当前文稿上下文
- 用户长期规则
- 项目规则

若用户没有配置规则，则 `system_prompt` 可以为空。

### 2.3 当前会话历史自动携带

每次 turn 自动携带当前激活会话的历史消息，但只限当前会话：

- 会话 A 的消息不会自动注入到会话 B
- 历史会话列表仅用于切换，不是默认上下文池
- `messages` 只承载当前会话里的 `user / assistant` 消息
- 规则、Skill、Agent system prompt 都不写回消息历史

`v1A` 中这里的“自动携带”，只表示 ordinary chat runtime 会把 request 中提供的 `messages` 视作当前会话历史输入；不表示服务端会再根据 `conversation_id` 静默补 hidden transcript。

### 2.3A 会话锚点与 turn 真值分层

`conversation_id` 与 `messages` 必须分层，不得在 `v1A` 就做成“双真值并存”。

`v1A` 正式口径直接定为：

- `conversation_id`
  - 是产品会话锚点
  - 用于会话切换、trace 聚合、当前会话持续 Skill 等 UI 语义
- `messages`
  - 是本轮 turn request 的 transcript 真值
  - 是 ordinary chat runtime 在 `v1A` 的正式输入快照
- `continuation_anchor`
  - 是请求级 continuation 锚点
  - 用于声明“本轮预期承接哪一个前序 run / transcript 视图”

`v1A` 规则：

- 在没有 server-side conversation truth 的 `v1A`，`conversation_id` 本身不提供跨请求冲突检测能力
- `continuation_anchor` 最少建议包含 `previous_run_id` 与可选 `messages_digest`
- 若请求提供 `continuation_anchor`，runtime 必须校验它与 `conversation_id`、`messages` 所表达的 direct-parent 关系；失败返回 `conversation_state_mismatch`
- 若请求未提供 `continuation_anchor`，runtime 只能把该请求视作该 `conversation_id` 下的新分支或无锚点请求，不得宣称已完成跨请求冲突检测
- 服务端不得仅凭 `conversation_id` 静默补历史、重排消息或拼隐藏上下文
- 若 `conversation_id` 与 `messages` 所表达的产品会话归属明显冲突，或与 `continuation_anchor` 校验结果冲突，必须显式失败或走显式迁移协议
- 在后端还没有正式 conversation store 之前，不定义“服务端持久会话历史”第二真值

后续若要升级到 server-side conversation truth，必须单独落正式会话存储与恢复协议，再显式调整本文口径；不能在 `v1A` 先把 request snapshot truth 和 server truth 混在一起。

### 2.4 Skill 是显式增强

Skill 的职责是“任务模板”，不是普通聊天的强制外壳。

Skill 只在以下场景参与：

- 用户本次显式指定 `skill_id`
- 当前会话显式绑定某个 Skill
- 内部流程显式调用某个内置 Skill

未显式选择 Skill 时，运行时直接按普通聊天模式执行。

### 2.5 Agent 是高级增强

Agent 的职责是封装更重的运行时组合能力，例如：

- 绑定特定 Skill
- 绑定模型或输出格式
- 绑定 MCP / Hook / 额外执行策略

Agent 不属于小说创作主路径的默认入口。

### 2.6 MCP 是能力层

MCP 的语义是“可用能力注册”，不是“把一大段 MCP 描述文本拼到 prompt 里”。

运行时只在以下场景让 MCP 参与：

- 某个 Hook 显式调用工具
- 某个 Agent 显式依赖工具能力
- ordinary chat 若进入通用 tool-calling，则由主 runtime 按实际调用回填工具结果，执行真值见 [22-assistant-tool-calling-runtime](./22-assistant-tool-calling-runtime.md)

仅仅“配置了 MCP”不代表每轮都要额外占用 prompt 预算。

### 2.7 内置 Skill 只用于内部流程

系统内置 Skill 仍然可以保留，但只建议用于内部能力，例如：

- 摘要提取
- 结构化抽取
- 内容分类
- 审核或后处理

系统内置 Skill 不应作为 Studio 普通聊天的默认主 Skill。

---

## 3. 运行时分层

### 3.1 默认聊天层

默认聊天层由以下部分构成：

1. `conversation_id` 对应的当前会话锚点
2. `continuation_anchor`
3. request 提供的当前会话历史 snapshot（`messages`）
4. 从 `messages` 末条业务消息派生的当前用户消息视图
5. 当前文稿上下文
6. 用户规则
7. 项目规则
8. 模型偏好 / 显式模型覆写

这条链路不要求 `skill_id` 或 `agent_id`。

这里的 `conversation_id` 只是 ordinary chat 的产品会话锚点，用于：

- 绑定“当前会话持续使用”的 Skill 等 UI 语义
- 聚合同一会话下的 turn / run / trace
- 为后续审批恢复、turn 去重和会话切换提供稳定归属

它不等同于 session 级写权限真值；写权限边界仍以 [22-assistant-tool-calling-runtime](./22-assistant-tool-calling-runtime.md) 中的 run / grant 协议为准。

`continuation_anchor` 则是请求级执行衔接锚点，用于：

- 绑定本轮预期直接承接的 `previous_run_id`
- 为 retry / replay / fork / resume 提供显式因果关系
- 在没有 server-side conversation truth 时承担最小冲突检测入口

`v1A` 还必须明确：

- `conversation_id` 负责产品归属，不负责补全隐藏 transcript
- `continuation_anchor` 才是跨请求 direct-parent 校验入口；没有它时，runtime 不声称具备冲突检测能力
- `messages` 是本轮请求级 transcript snapshot 真值
- `当前用户消息` 若在 runtime 内部被单独引用，也只能是 `messages` 中最后一条 `user` 业务消息的派生视图，不是独立 request 字段
- `run_id` 是 turn 级执行真值，后续审批、恢复、幂等、SSE 时序都绑定 `run_id`

### 3.1A 输入 / 输出 item 分层口径

本层还需要再收死一个边界：

- `system_prompt + prompt`
  - 是 `v1A` 当前代码里真正发送给 provider 的文本装配投影
- `PromptSection[]`
  - 仍只是后续重构目标，不是当前代码里的 first-class 运行时对象
  - 即使后续引入，也只负责装配、预算与 provider request projection
- `NormalizedInputItem[]`
  - 是 run snapshot / continuation / replay 真值
  - 负责承载需要被恢复、审计、审批复用的系统语义
- `AssistantOutputItem[]`
  - 是模型输出归一化真值
  - 负责承载 `text / tool_call / tool_result / reasoning / refusal` 等 item 级结果

当前代码已经不再只有“一个 content 字段”的输出真值；输入侧则仍处在 `system_prompt + prompt` 到更结构化装配模型的过渡阶段。

具体 item taxonomy 与字段边界统一以 [22-assistant-tool-calling-runtime](./22-assistant-tool-calling-runtime.md) 为准，本文只定义主路径的分层口径。

### 3.1B 当前 Prompt 装配真值（`v1A`）

当前 ordinary chat 发给 provider 的输入，仍然是两个文本槽位：

- `system_prompt`
- `prompt`

其中：

- `system_prompt`
  - 由 `base_system_prompt` 与规则层拼接生成
  - 当前实际顺序是：基础 system prompt -> 规则前导语 -> 用户规则 -> 项目规则
- `prompt`
  - 由 ordinary chat / Skill 装配逻辑渲染成文本
  - 当前仍不是 first-class `PromptSection[]`

默认聊天模式下，`prompt` 当前实际顺序是：

1. 若存在压缩后的早期历史摘要，则先放 `【压缩后的早期对话摘要】`
2. 若存在保留历史，则放 `【当前会话历史】`
3. 若存在 `document_context`，则放 `【当前文稿上下文】`
4. 若命中项目范围启发式提示，则放 `【项目范围工具提示】`
5. 最后放 `【用户当前消息】`

Skill 模式下，`prompt` 当前实际顺序是：

1. 总是先放 `【当前 Skill 指令】`
2. 若 Skill 未显式接管历史，则追加 `【当前会话历史】`
3. 若存在 `document_context`，则追加 `【当前文稿上下文】`
4. 若命中项目范围启发式提示，则追加 `【项目范围工具提示】`
5. 若 Skill 未显式接管当前输入，则最后追加 `【用户当前消息】`

补充规则：

- 若 Skill 显式引用 `messages_json`，当前实现不再自动补会话历史和用户当前消息，但仍会追加项目文稿上下文或项目范围提示
- `project.search_documents / project.read_documents` 的启发式提示目前仍是真实 prompt 行为，不是隐藏实现；它只影响提示文本，不改变工具可见性真值
- 该提示当前在 prepare 阶段只冻结一次，并同时进入 prompt 与 run snapshot 的 `NormalizedInputItem(item_type=tool_guidance)`，不再由 prompt render 二次重算
- `PromptSection[]`、稳定前缀 / 易变后缀排序与 cache hint 仍属于后续重构目标，当前不作为本节正式真值

与文本装配分层的正式持久化对象仍是 `NormalizedInputItem[]`。当前至少写入：

- `message`
- `compacted_context`
- 用户 / 项目规则
- `skill_instruction`
- `hook_selection`
- `model_selection`
- flat `document_context`
- `document_context_binding`
- `document_context_recovery`
- 归一化后的 `document_context_binding`

### 3.2 规则层

规则是长期自动增强，属于“每个 turn 默认携带”的层。

规则来源：

- 用户层：`users/<user_id>/AGENTS.md`
- 项目层：`projects/<project_id>/AGENTS.md`

叠加顺序：

`用户规则 -> 项目规则`

项目规则更具体，优先级高于用户规则。

当前规则模型的正式口径是：

- 每个作用域仍只有一份主 `AGENTS.md` 作为设置页读写入口
- runtime `rule bundle` 当前仍只有 `user_content / project_content` 两段最终装配真值
- 主 `AGENTS.md` 的 YAML frontmatter 当前允许显式声明同作用域 `include` 列表；运行时会在 build rule bundle 时按声明顺序递归展开
- include 只允许停留在当前 `user` / `project` 作用域目录内；循环 include、缺失文件、越出作用域根目录都直接报错

### 3.2A Platform Safety Baseline

平台级安全基线不属于“用户规则 / 项目规则”的覆盖链。

它的职责是：

- 承载不可被普通规则覆盖的系统底线
- 与创作风格、项目约束、用户偏好分层
- 在 provider 适配、tool policy、审计回放里保持同一口径

约束：

- 平台安全基线不写回 `messages`
- 平台安全基线不通过“项目规则优先于用户规则”这条链参与覆盖
- 它属于 runtime 的硬约束层，不得被用户规则、项目规则或 Skill 文本静默改写

### 3.3 Skill 层

Skill 是显式增强层。

行为规则：

- 未显式选择时，不参与运行时
- 选中后，由 Skill 渲染 prompt
- Skill 只覆盖当前 turn 或当前会话，具体由 UI 入口决定

Skill 解析顺序：

`项目层 -> 用户层 -> 系统层`

但只有在显式引用同一个 `skill_id` 时，这个覆盖规则才成立。

### 3.4 Agent 层

Agent 是显式高级层。

行为规则：

- 普通聊天不默认进入 Agent
- 进入 Agent 后，由 Agent 决定绑定的 Skill、模型和额外能力
- Agent 仍然会继承规则层

### 3.5 MCP 层

MCP 是能力层，不是模板层。

行为规则：

- 不自动拼接成常驻 prompt
- 只有工具实际调用时，其结果才进入本轮上下文
- ordinary chat 的通用 tool-calling 执行链、provider 适配和 SSE 真值统一见 [22-assistant-tool-calling-runtime](./22-assistant-tool-calling-runtime.md)
- 解析顺序仍为 `项目层 -> 用户层 -> 系统层`

---

## 4. 默认 turn 装配流程

本文只定义主路径的语义装配，不再把 ordinary chat 冻结成“单次调用上游模型”的旧执行链。

- 具体 tool loop、provider adapter、run/step 真值、SSE 协议见 [22-assistant-tool-calling-runtime](./22-assistant-tool-calling-runtime.md)
- 本节只回答“每轮 turn 需要先装配哪些输入、再把执行控制交给哪一层”

每次用户发送消息时，assistant runtime 按以下顺序装配 turn：

1. 解析当前 `conversation_id`
2. 解析当前 `continuation_anchor`
3. 读取 request 中的当前会话消息 snapshot（`messages`）
4. 校验最后一条业务消息必须是 `user`，并将其派生为“当前用户消息”视图
5. 解析项目作用域
6. 解析 AI 偏好与模型覆写
7. 读取用户规则和项目规则
8. 判断当前模式：
   - 有 `agent_id`：Agent 模式
   - 否则有 `skill_id`：Skill 模式
   - 否则：默认聊天模式
9. 组装本轮结构化 turn 输入：
   - `conversation_id`
   - `continuation_anchor`
   - 当前会话历史
   - 当前用户消息（派生视图，不是第二份 request 真值）
   - 当前文稿上下文
   - `requested_write_scope`
   - `requested_write_targets`
   - 兼容扩展袋 `input_data`
   - 用户规则与项目规则
   - 模型偏好 / 显式模型覆写
   - 当前模式需要的额外装配项
10. 将执行控制交给当前模式对应的 runtime：
   - 默认聊天模式：ordinary chat runtime，执行真值见 [22-assistant-tool-calling-runtime](./22-assistant-tool-calling-runtime.md)
   - Skill / Agent 模式：仍遵守本主路径语义，但可叠加各自模板、策略和能力
11. 若本轮发生工具调用，只把实际调用结果写回本轮上下文，不把工具声明常驻写入消息历史
12. 取得最终回复后，由产品持久化层按显式协议写回当前会话；该持久化不反向改写本轮 request snapshot truth

默认聊天模式的主语义保持为：

- `conversation_id`
- `continuation_anchor`
- `当前会话历史`
- `用户当前消息（由 messages 末项派生）`
- `当前文稿上下文`
- `requested_write_scope / requested_write_targets`
- `用户规则与项目规则`
- `模型偏好 / 显式模型覆写`

这些输入可以在内部以结构化 turn context 传递，不要求继续硬编码成“只有两段 prompt 文本”。

兼容迁移口径：

- `conversation_id` 是新的正式会话锚点；即使迁移期仍由前端传完整 `messages`，也不再只依赖前端本地 active conversation state 作为唯一真值
- `continuation_anchor` 是新的正式 continuation 输入；`v1A` 最少应能落到 `previous_run_id + messages_digest(optional)`
- `v1A` 采用 request snapshot truth：`messages` 是本轮 transcript 真值，`conversation_id` 只负责产品会话归属
- `当前用户消息` 若在运行时内部被单独使用，只能由 `messages` 末条 `user` 业务消息派生，不再并行引入第二个 request 字段
- 在正式 conversation store 落地前，服务端不得根据 `conversation_id` 静默回填未出现在 request 中的历史消息
- 在没有 server-side conversation truth 的 `v1A`，只有命中 `continuation_anchor` 的 direct-parent 校验时，runtime 才可判定 `conversation_state_mismatch`
- 若产品层存在 conversation store 或 turn 持久化，它也只是后续 UI 恢复 / 装配的候选来源，不得在当前 run 创建后反向改写本轮 snapshot truth
- `document_context` 是新的正式系统字段
- `document_context` 最少应能落到 `active_path / active_document_ref / active_binding_version / selected_paths / selected_document_refs / active_buffer_state.base_version / catalog_version`
- flat `document_context` 只是 request projection；runtime 内部应尽快归一化成带 `binding_version` 的 `DocumentContextBinding[]`
- `document_context` 的长期三层映射应固定为：
  - request projection：前端 / API 透传的 `document_context`
  - runtime normalized binding：ordinary chat runtime 内部冻结到 run snapshot 的 `DocumentContextBinding[]`
  - project binding：项目文稿能力层消费的 `ProjectDocumentContextBinding`
- 除了原始 request projection 和 normalized binding 之外，`AssistantTurnRun` 当前还会显式冻结 `document_context_recovery_snapshot`，作为“基于 bindings 回放后的 latest recovery view”；它用于保留 runtime 真正应恢复的活动文稿、binding version、selected refs/paths 与 active buffer state，不再要求恢复链临时从两份旧 snapshot 重新拼装
- `AssistantTurnRun` 当前还会显式冻结 `document_context_injection_snapshot`，作为 latest recovery view 经过 prompt-visible projection 后的单一注入真值；prepare 阶段只生成一次，后续 prompt projection / prompt render / run snapshot / hook payload 共享同一份 injection view，不再从 `document_context_snapshot + bindings_snapshot` 现推
- 若当前 Studio 存在活动编辑器，`active_buffer_state` 必须随 turn request 一起透传；runtime 不反向读取前端本地编辑缓冲区
- 若活动文稿可能成为本轮读写目标，但请求里缺失可信 `active_buffer_state`，runtime 不能猜测其缓冲区状态，只能拒绝对该文稿签发写入 grant
- `requested_write_scope` 与 `requested_write_targets` 必须分层；前者回答“本轮有没有写能力”，后者回答“哪些文稿可成为候选写目标”
- `requested_write_targets` 的长期 request 形状固定为 `document_ref[]`，不再在 request 层混用 path 与 document_ref
- 若 `requested_write_targets` 缺失，`v1A` 默认只把当前 `active_document_ref` 视为候选写目标
- `v1A` 实际只接受“缺失”或“仅包含当前 `active_document_ref` 的单元素集合”；若显式传入其他目标，必须返回显式错误，而不是静默放宽
- `selected_paths / selected_document_refs` 只是读取/参考集合，不是隐式写入白名单
- `input_data` 在迁移期继续保留，只作为现有 Skill / Hook / Agent 的兼容扩展袋
- 新的系统级文稿上下文不再继续写进 `input_data`
- Hook payload 在迁移期同时暴露 `request.input_data` 与 `request.document_context`
- 当前 `before_assistant_response / after_assistant_response` hook payload 还会同步暴露 latest `request.document_context_bindings_snapshot`、`request.document_context_recovery_snapshot`、`request.document_context_injection_snapshot`、`request.compaction_snapshot`、`request.tool_guidance_snapshot`、`request.tool_catalog_version` 与 `request.exposed_tool_names_snapshot`，让 hook 与 turn snapshot 共享同一份 context governance / tool exposure 真值
- 当前 prompt 层的“项目范围工具提示”仍是 ordinary chat 的显式装配逻辑：prepare 阶段会先基于项目作用域、文稿上下文缺席、continuity 关键词命中与本轮实际 visible tools 解析 internal discovery decision，只有当 `project.search_documents / project.read_documents` 真实同时可见时才会决议为 `project_search_then_read`
- 该提示仍不是独立的 tool discovery phase；工具暴露真值继续以 [22-assistant-tool-calling-runtime](./22-assistant-tool-calling-runtime.md) 的 exposure policy 为准，但 guidance 本身不再直接从“候选关键词命中”冻结，而是由 resolved discovery decision 投影出来
- 该提示当前会以显式 `tool_guidance` snapshot 冻结，至少包含 `guidance_type / tool_names / trigger_keywords / discovery_source / content`；resolved discovery decision 投影出的 guidance 才会进入 `AssistantTurnContext / AssistantTurnRunSnapshot / AssistantTurnRun`，并被 prompt projection / prompt render 与 `NormalizedInputItem(item_type=tool_guidance)` 共同消费，不再在渲染阶段按消息和文稿上下文重新启发式计算

上下文压缩口径：

- 当前实现会在 turn 入口对较早历史做单阶段摘要压缩，不直接改写 `messages` transcript 真值
- 触发条件是：按当前 `system_prompt + prompt + tools` 估算后，输入超过 `max_input_tokens`
- 当前这段只描述 turn 入口的历史压缩；tool loop continuation items 的预算收口统一见 [22-assistant-tool-calling-runtime](./22-assistant-tool-calling-runtime.md)，不在本文重复定义
- 当前用户消息不会被压缩；`document_context` 通过受保护路径参与摘要构造，不会被静默丢失
- 若 Skill 显式使用 `messages_json`，或没有可压缩的更早历史，当前实现会直接返回 `budget_exhausted`
- compaction 成功后，会同时留下：
  - prompt 中的 `【压缩后的早期对话摘要】`
  - run snapshot 里的 `compaction_snapshot`
  - `NormalizedInputItem(item_type=compacted_context)`，其中 `content` 保留摘要文本，`payload` 直接复用完整 `compaction_snapshot`
- `compaction_snapshot` 当前除了 `protected_document_paths` 之外，还会显式冻结当前可解析到的 `compressed_messages_digest`、压缩后实际消息投影视图的 `projected_messages_digest`、`summary_anchor_keywords`、`protected_document_refs`、`protected_document_reasons`、`protected_document_binding_versions`、`document_context_collapsed`、`document_context_projection_mode`、`projected_document_context_snapshot` 与 latest `document_context_recovery_snapshot`；其中 `projected_document_context_snapshot` 与 `document_context_injection_snapshot` 当前应保持同一份 prompt-visible recovery 真值，让 compaction audit 能直接对齐被压缩消息切片、压缩后消息视图、摘要锚点、binding / recovery 真值，以及 prompt 最终保留的文稿上下文层级，而不再只依赖路径字符串
- 当前 `compaction_snapshot` 已至少包含：
  - `phase=initial_prompt`
  - `level=soft|hard`
  - `soft` 表示摘要之外至少还保留了一段最近原始消息
  - `hard` 表示早期历史已完全折叠到摘要里，不再保留最近原始消息槽
- `fail` 当前不进入 snapshot；若初始 prompt 在压缩后仍无法落入预算，会显式返回共享 `budget_exhausted` 终止错误
  - `trigger_reason / budget_limit_tokens / estimated_tokens_before / estimated_tokens_after`
  - `document_context_collapsed=false|true`
  - `document_context_projection_mode=full|active_only|selected_only|omitted`
- 当前 v1 已正式落地 latest compaction / context collapse / recovery 合同；若后续需要多次 compaction 的完整历史链，再另起计划，不回滚这里的单真值口径

长期记忆口径：

- 用户长期偏好继续由用户规则承载
- 项目长期约束继续由项目规则承载
- 项目事实继续由项目文稿、`ProjectSetting` 与其他正式业务真值承载
- 会话连续性继续由 `conversation_id + messages + run snapshot` 承载
- `v1A / v1B` 不新增独立 assistant memory 真值层，避免在规则、文稿、会话之外再制造一套自由记忆真值

用户规则和项目规则如果存在，则仍可通过 `system_prompt` 或等价结构化字段注入；若不存在，则该层留空。

Skill 模式的装配规则：

- 总是先放当前 Skill 指令
- 若 Skill 模板没有显式引用 `conversation_history`，运行时自动追加“当前会话历史”语义
- 若 Skill 模板没有显式引用 `user_input`，运行时自动追加“当前用户消息”语义
- 若 Skill 模板显式引用 `messages_json`，视为它已自行接管整段消息上下文，运行时不再重复追加历史或当前消息
- 文稿上下文、规则和模型选择仍通过主路径装配进入 runtime，不因 Skill 模式丢失
- 当前代码里基于模板引用变量名的自动追加逻辑只视为兼容口径，不作为长期唯一真值
- 后续若要增强 Skill 装配控制，应显式落到独立 `SkillAssemblyPolicy` 或等价结构化对象，而不是继续把变量名探测扩成隐式策略系统

这样可以保证：

- Skill 模式默认仍遵守“规则 + Skill + 历史 + 当前消息”的主语义
- 老 Skill 如果已经自己声明 `conversation_history / user_input / messages_json`，不会出现重复上下文

---

## 5. 产品交互建议

### 5.1 Studio 默认模式

Studio 默认进入“普通对话”。

不默认显示：

- 系统内置 Skill 已启用
- 系统内置 Agent 已启用
- 系统内置创作 prompt 已启用

### 5.2 Skill 选择

Skill 应提供显式选择入口，但不抢占主路径。

当前支持两种语义：

- 本次使用一次
- 当前会话持续使用

默认值始终是“无 Skill”。

### 5.3 Agent 与 MCP

Agent、MCP 维持高级入口即可。

对小说创作产品，一线心智仍应是：

- 规则
- 文稿上下文
- 当前会话
- 模型连接

而不是把 Agent / MCP 变成日常写作聊天的必选项。

---

## 6. 与现有能力的边界

以下内部流程仍可继续显式使用内置 Skill：

- 项目摘要提取
- 自由文本设定结构化
- 审核 / 后处理链路

这些流程不与普通聊天主路径冲突，因为它们属于“系统内部能力调用”，不是“用户默认创作聊天入口”。

---

## 7. 文档使用说明

后续涉及 assistant 主路径时，优先参考：

1. 本文档：assistant 主路径语义、分层与默认装配边界
2. [22-assistant-tool-calling-runtime](./22-assistant-tool-calling-runtime.md)：ordinary chat tool-calling runtime、tool loop、run/step 真值、SSE 语义
3. [21-assistant-project-document-tools](./21-assistant-project-document-tools.md)：项目文稿工具域、统一目录、读写/版本/revision 约束
4. [系统架构设计](../specs/architecture.md)
5. [配置格式规范](../specs/config-format.md)
6. [16-mcp-architecture](./16-mcp-architecture.md)：只作为 MCP client/plugin 当前基线与历史背景，不再作为 ordinary chat native tool runtime 的未来真值
7. 当前代码实现

旧的实施计划文档只作为历史背景，不作为当前运行时真值。
