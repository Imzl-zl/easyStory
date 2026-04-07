# Assistant Runtime 文档重构计划

> 文档状态：进行中
>
> 当前 assistant runtime 的正式设计真值仍以 [20-assistant-runtime-chat-mode](../design/20-assistant-runtime-chat-mode.md)、[22-assistant-tool-calling-runtime](../design/22-assistant-tool-calling-runtime.md)、[21-assistant-project-document-tools](../design/21-assistant-project-document-tools.md)、相关 `docs/specs/*.md` 与当前代码为准。
>
> 本文只记录改造期间的迁移路线、章节归属、待改造主题和退出条件，不单独代表当前正式运行时真值。
>
> 若你要继续 assistant `service/` 内部目录标准化的逐步迁移顺序，请看 [Assistant Service 目录迁移路线图](./2026-04-07-assistant-service-package-roadmap.md)。

## 1. 目标

这轮改造的目的不是再新增一套 assistant 设计，而是把后续要吸收的优化点先有序落到“迁移路线”里，避免出现以下问题：

- 新旧语义零散混写在 `20/21/22` 各处，读者分不清哪些已经生效
- 目标设计写进计划文档后长期不回写，形成事实上的第二套真值
- 为了记录过渡状态而继续扩张 design 文档顶部或末尾的“临时说明”

本计划的核心任务是先把“怎么改文档”讲清楚，再按章节逐步回写正式设计。

结合 2026-04-07 的最新源码审查，当前已确认：

- `document_context` 已具备 `request projection -> runtime normalized binding -> project binding` 的基础闭环，不应再按“纯待设计”处理
- 本轮已完成 `tool_catalog_version` 独立化，当前由“本轮最终可见 descriptor 快照版本”稳定派生
- assistant 内部目录标准化已完成十个稳定子域：turn 生命周期文件已收口到 `service/turn/`，tooling descriptor/policy/executor/loop/store 文件已收口到 `service/tooling/`，context 纯 support 文件已收口到 `service/context/`，hook runtime 文件已收口到 `service/hooks_runtime/`，rules DTO/service/support 文件已收口到 `service/rules/`，preferences DTO/service/support 文件已收口到 `service/preferences/`，skills DTO/file-store/service/support 文件已收口到 `service/skills/`，agents DTO/file-store/service/support 文件已收口到 `service/agents/`，mcp DTO/file-store/service/support 文件已收口到 `service/mcp/`，hooks 配置 DTO/file-store/service/support 文件已收口到 `service/hooks/`
- 根壳再评估已完成：`assistant_service.py / factory.py / dto.py` 等继续保留为组合壳；唯一额外收口是把 prompt render 从 `assistant_execution_support.py` 抽回 `service/context/assistant_prompt_render_support.py`
- 分级 compaction、规则 include / 拆分、first-class tool discovery 仍未进入代码真值，暂不应在正式设计里冒充现状

## 2. 文档边界

### 2.1 正式真值

以下内容继续视为正式真值：

1. `docs/specs/*.md`
2. `docs/design/20-assistant-runtime-chat-mode.md`
3. `docs/design/22-assistant-tool-calling-runtime.md`
4. `docs/design/21-assistant-project-document-tools.md`
5. 当前代码实现

### 2.2 临时改造文档

`docs/plans/2026-04-07-assistant-runtime-doc-refactor.md` 只负责：

- 记录待迁移主题
- 记录每个主题最终应回写到哪份正式设计
- 记录改造顺序和阶段状态
- 记录改造完成后的退出条件

它不负责：

- 重新定义完整 assistant runtime 正式语义
- 复制 `20/21/22` 的整章内容
- 在 design 真值之外长期并行存在

### 2.3 顶部声明规则

改造期间，`20/21/22` 顶部只增加短导航声明：

- 本文仍是正式设计真值
- 改造路线看本计划
- 未明确回写到本文的目标语义，不视为正式真值

禁止把待迁移条目、未来愿景或长 TODO 直接堆到正式设计文档顶部。

## 3. 最优改造方式

当前最优做法不是再拆一组 `20A / 22A` 新设计文档，而是采用下面这条路径：

1. 保留 `20/21/22` 作为唯一正式 assistant runtime 设计入口
2. 用一份计划文档承载迁移路线和待改造章节
3. 按主题逐节回写正式设计，而不是先写“未来版完整文档”
4. 每回写完一组主题，就从本计划里删掉或标记已完成
5. 改造结束后，把本计划降级为历史实施记录

这样做的好处是：

- 真值入口始终稳定
- 改造期可以允许临时过渡信息存在
- 过渡信息不会长期污染正式设计正文
- 读者不会被两套“看起来都像真值”的 assistant 文档误导

## 4. 待吸收的改造主题

这些主题来自当前源码审查结果，以及对 Claude Code 工具系统 / 上下文工程 / 规则治理方式的借鉴，但必须按 easyStory 的产品边界落地，不能照搬 CLI 心智。

### 4.1 Tool Governance

要吸收的点：

- 延迟工具加载与按需发现，而不是默认全量暴露
- 类似 `ToolSearch` 的工具发现路径，替代 prompt 里的关键词启发式提示
- 更完整的工具治理元数据：`aliases`、`result_budget`、`search_hint`、`concurrency_class`、`destructive_class`
- `tool_catalog_version` 与文稿目录版本彻底解耦

当前阶段收口：

- 本轮已把 `tool_catalog_version` 从 `document_context.catalog_version` 拆出
- `v1A / v1B` 当前不新增独立 `search_tools` 工具
- 独立后的 `tool_catalog_version` 先收口为“本轮最终可见 descriptor 快照版本”，后续再评估是否补单独 catalog assembler / discovery phase

正式归属：

- 主归属 [22-assistant-tool-calling-runtime](../design/22-assistant-tool-calling-runtime.md)
- 涉及 ordinary chat 入口提示收口时，回写 [20-assistant-runtime-chat-mode](../design/20-assistant-runtime-chat-mode.md)

### 4.2 Context Governance

要吸收的点：

- 分级 compaction，而不只是单次 summary fallback
- context collapse 后的显式恢复注入
- `document_context` 单真值继续向 normalized binding 收口
- 大结果外置或预览化，避免工具结果无界回填
- 稳定前缀 / 易变后缀的 prompt section 组织方式

当前源码结论：

- ordinary chat 已具备单阶段历史摘要压缩
- initial prompt compaction snapshot 已具备 `phase / level` 显式元信息
- `continuation_anchor_snapshot` 已归一化冻结 validated direct-parent digest，不再只是客户端原样回显
- latest continuation request view 已进入显式 `continuation_request_snapshot`
- latest tool loop continuation budget compaction 已进入显式 `continuation_compaction_snapshot`
- `document_context` 已通过 normalized binding 进入 run snapshot、grant 与 project capability
- 项目范围工具提示已同时进入 prompt 与 `NormalizedInputItem(item_type=tool_guidance)`，且当前由 prepare 阶段冻结一次后复用于 prompt render 与 run snapshot，不再在 prompt 渲染阶段二次重算
- 分级 compaction / collapse / recovery 仍未落地为正式代码真值

正式归属：

- 主归属 [20-assistant-runtime-chat-mode](../design/20-assistant-runtime-chat-mode.md)
- tool loop / run snapshot / continuation 相关合同回写 [22-assistant-tool-calling-runtime](../design/22-assistant-tool-calling-runtime.md)

### 4.3 Rule Governance

要吸收的点：

- 在“用户层 / 项目层”各自作用域内支持规则拆分和 include
- 保持作用域模型不变，不引入目录上溯式自动发现
- 让规则装配顺序更稳定，更利于 cache 和审计

正式归属：

- 主归属 [20-assistant-runtime-chat-mode](../design/20-assistant-runtime-chat-mode.md)

### 4.4 Project Document Tool Domain

要继续保持的边界：

- 仍然是“项目文稿能力域”，不是通用文件系统代理
- 文稿 identity / version / revision / trusted snapshot 继续由 `project` 域定义
- 不因为引入更强 tool governance 就把 `21` 扩张成通用 runtime 文档

正式归属：

- 主归属 [21-assistant-project-document-tools](../design/21-assistant-project-document-tools.md)

### 4.5 已确认的借鉴结论

本轮已经确认以下取舍，后续实现与正式设计回写应以此为准。

采纳项：

- 借鉴 Claude Code 的工具治理思路，但不照搬 CLI 式单体 `Tool` 抽象；easyStory 继续采用 `descriptor -> catalog/exposure -> policy -> executor -> result/audit` 分层。
- 工具发现先采用 runtime 内部两阶段 contract：`CatalogAssembler` 组装候选池，`ExposurePolicy` 收口可见集合；`v1A / v1B` 不先暴露独立 `search_tools` 工具给模型。
- ordinary chat 的正常结束继续由模型决定：只有模型不再返回 tool call，run 才正常完成；预算、取消、安全边界、状态持久化失败等仍由 runtime 硬终止。
- 上下文压缩采用分级策略：至少区分软压缩、硬压缩、终止级失败，不再只保留单次 summary fallback。
- 审计分类进入 `AssistantToolResultEnvelope.audit` 或等价 step audit 元数据，不单独新增并行顶层真值字段，命名统一为 `risk_class`。

暂不采纳项：

- 不引入 Claude Code 风格的 monolithic tool 对象，同时承载 schema、可见性、执行、UI projection 与权限。
- 不引入独立的 assistant memory 真值层；长期偏好继续由用户 / 项目规则承载，项目事实继续由项目文稿与 `ProjectSetting` 承载。
- 不在 `v1A / v1B` 直接上“流式工具预执行”；只有在 streamed tool arguments 具备稳定闭合语义、且限定到安全只读工具时，才考虑后续评估。

实现优先级：

1. 已完成 `tool_catalog_version` 语义独立化（代码 / 测试 / 正式设计同步）
2. 下一优先级是 `20 + 22` 的 compaction / context recovery / tool hint 收口
3. 之后再评估规则 include 与流式预执行之类的增强项

## 5. 章节归属与迁移顺序

| 主题 | 正式归属 | 当前状态 | 说明 |
|---|---|---|---|
| tool exposure / policy 合同补全 | `22` | DONE | 已按当前实现回写 `DescriptorRegistry -> ExposurePolicy -> PolicyResolver -> Executor` 边界，不再把未落地组件写成现状 |
| `tool_catalog_version` 语义独立化 | `22` | DONE | 当前已改为独立的 visible descriptor snapshot version，不再借用 `document_context.catalog_version` |
| `continuation_anchor` 恢复锚点归一化 | `22` | DONE | `AssistantTurnRun.continuation_anchor_snapshot` 当前会显式冻结 validated direct-parent digest，不再在省略 `messages_digest` 时只剩 `previous_run_id` |
| latest continuation request view 冻结 | `22` | DONE | `AssistantTurnRun` 当前已显式保存 latest `continuation_request_snapshot`，并与 `provider_continuation_state / continuation_compaction_snapshot` 分离 |
| assistant 内部目录标准化（`turn / tooling / context / hooks_runtime / rules / preferences / skills / agents / mcp / hooks`） | 实现 | DONE | turn 生命周期文件当前统一位于 `service/turn/`，tooling descriptor/policy/executor/loop/store 文件当前统一位于 `service/tooling/`，context 纯 support 文件当前统一位于 `service/context/`，hook runtime 文件当前统一位于 `service/hooks_runtime/`，rules DTO/service/support 当前统一位于 `service/rules/`，preferences DTO/service/support 当前统一位于 `service/preferences/`，skills DTO/file-store/service/support 当前统一位于 `service/skills/`，agents DTO/file-store/service/support 当前统一位于 `service/agents/`，mcp DTO/file-store/service/support 当前统一位于 `service/mcp/`，hooks 配置 DTO/file-store/service/support 当前统一位于 `service/hooks/` |
| `document_context` 单真值收口 | `20 + 21 + 22` | IN_PROGRESS | request projection、normalized binding、project binding 已有代码基础；后续主要剩 recovery / compaction / 审计语义继续收口 |
| ordinary chat 启发式工具提示收口 | `20` | IN_PROGRESS | 当前仍是实际 prompt 装配行为，但已收口为“prepare 阶段冻结一次 `tool_guidance` snapshot，再由 prompt render 与 run snapshot 共同消费”；只有等真正的 tool discovery 落地后，才能从 design 中移除 |
| 分级 compaction / collapse / 恢复 | `20 + 22` | IN_PROGRESS | 当前已落地 turn 入口历史摘要压缩、`phase / level` 元信息、latest `continuation_request_snapshot`、tool loop continuation projection 的预算收口，以及 latest `continuation_compaction_snapshot` 审计；更完整的分级 compaction、collapse、history audit 与 recovery 仍未成为代码真值 |
| 规则拆分 / include | `20` | TODO | 当前规则仍是单文件装配；后续仅在“用户层 / 项目层”现有作用域内做 include / 拆分，不改全局作用域模型 |

推荐迁移顺序：

1. 先推进 `20 + 22` 的 compaction / context recovery / tool hint 收口
2. 之后再处理 `20` 的规则拆分 / include
3. 最后回看 `21`，只补与项目文稿工具域直接相关的新增约束

## 6. 改造期间的写法规则

在正式设计文档中：

- 只写已经确认要成为正式真值的内容
- 一次回写一个主题块
- 如果某主题仍在讨论，留在本计划，不要提前写进 design

在本计划中：

- 不复制完整正式设计
- 只记录迁移目标、主题归属、阶段状态和未完成项
- 一旦正式设计已经回写，就删掉对应“待迁移”描述或标记完成
- 若源码已经形成稳定基线，应先把状态从 `TODO` 调整为 `IN_PROGRESS / DONE`，避免计划继续落后于实现

## 7. 退出条件

满足以下条件后，本计划应降级为历史实施记录：

1. `20/21/22` 已分别吸收各自主归属主题
2. design 文档之间不再依赖“临时迁移说明”才能理解边界
3. 读者只看 `docs/specs + docs/design + 当前代码` 就能得到完整正确语义
4. 本计划不再承载任何未回写的核心 assistant runtime 设计

到那时，计划文档顶部应改成“历史实施记录”，不再作为当前迁移入口。
