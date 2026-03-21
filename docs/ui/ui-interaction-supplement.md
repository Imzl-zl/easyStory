# easyStory UI 交互补充规格（MVP 对齐版）

| 字段 | 内容 |
|---|---|
| 文档类型 | UI 交互规则与实施补充 |
| 文档状态 | 生效 |
| 创建时间 | 2026-03-16 |
| 最后更新 | 2026-03-21 |
| 关联文档 | [设计索引](../design/00-index.md)、[UI 白皮书](./ui-design.md)、[系统架构](../specs/architecture.md) |

> 本文档定义当前前后端联调阶段的交互真值：能力矩阵、状态映射、页面层级、响应式、无障碍和边界态。它不重写产品设计，只负责把当前可实施范围钉死。
---
## 1. 文档定位
### 1.1 本轮适用范围

- 优先服务当前后端已落地接口。
- 可以保留未来能力的视觉预留，但不得假装已经具备完整闭环。
- UI 如果需要表达设计预留，必须明确标注 `MVP UI 占位` 或 `Future`。
### 1.2 本轮不作为当前真值的能力

- `Dry-run` 成本预估
- Workflow / Skill Schema 静态校验弹窗
- 运行时切换手动 / 自动模式
- 小说上传、自动采样、自动分析流水线
- Prompt Lab、模拟执行、保存为 Skill
- 回收站永久删除
- 忘记密码
- 高级导出格式（如 EPUB / PDF / DOCX）
- Story Bible 完整编辑工作台
- 伏笔追踪生产级可视化面板
---
## 2. 当前后端能力矩阵

| 领域 | UI 位置 | 当前能力 | 实施标记 |
|---|---|---|---|
| Auth | `Auth` | 注册、登录 | `MVP 已支持` |
| Project | `Lobby` / `Studio` | 创建、列表、详情、更新、软删除、恢复、项目设定更新、完整度检查 | `MVP 已支持` |
| Content | `Studio` | `Outline`/`OpeningPlan` 保存与确认，章节列表/详情/保存/确认，版本列表/回滚/最佳版本 | `MVP 已支持` |
| Workflow | `Engine` | 启动、详情、暂停、恢复、取消、章节任务重建、任务列表、任务编辑 | `MVP 已支持` |
| Credential | 全局设置 | 用户/项目级凭证列表、创建、更新、删除、验证、启用、停用 | `MVP 已支持` |
| Analysis | `Lab` | 新建分析、列表、详情 | `MVP 已支持` |
| Review | `Engine` | 审核摘要、审核动作列表 | `MVP 已支持` |
| Billing | `Engine` | 工作流账单摘要、Token 使用明细 | `MVP 已支持` |
| Context | `Engine` | 上下文预览 | `MVP 已支持` |
| Observability | `Engine` | 节点执行、执行日志、SSE 事件流、Prompt 回放 | `MVP 已支持` |
| Export | `Engine` | 项目导出列表、按工作流创建导出、下载导出文件 | `MVP 已支持` |
### 2.1 UI 必须按当前后端收口的点

- `Auth` 只做注册 / 登录，不出现忘记密码流程。
- `Export` 只支持 `txt` 与 `markdown`。
- `Lab` 当前定义为“分析结果工作台”，不是“上传原著自动风格提取”。
- `Recycle Bin` 当前只支持恢复，不暴露永久删除。
- `Engine` 中的模式展示为只读状态，不提供运行时切换控件。
- `Credential Center` 属于当前 MVP 的真实子模块，不再按占位入口处理。
---
## 3. 路由与视图层级真值

```text
/auth
  /login
  /register

/workspace
  /lobby
    /new -> incubator
    /recycle-bin
    /settings

  /project/:projectId/studio
    ?panel=setting|outline|opening-plan|chapter
    ?chapter=1
    ?versionPanel=1

  /project/:projectId/engine
    ?workflow=:workflowId
    ?tab=overview|tasks|reviews|billing|logs|context|replays
    ?export=1

  /project/:projectId/lab
    ?analysis=:analysisId
    ?mode=list|create
```

规则：

- `Lobby / Studio / Engine / Lab` 是主视图，不再新增同级页面。
- `Incubator / Recycle Bin / Export Dialog / Version Panel` 是子视图，不升级为一级路由主干。
- `Review & Diff` 属于 `Engine` 的 workflow 子视图；`Studio` 最多提供跳转入口，不直接承载审核数据面板。
---
## 4. UI 状态映射
### 4.1 项目状态

| 后端字段 | UI 展示 | 行为 |
|---|---|---|
| `status=draft` | 草稿项目 | 可继续补设定 |
| `status=active` | 创作中 | 进入工作台 |
| `status=completed` | 已完成 | 允许查看与导出 |
| `status=archived` | 已归档 | 默认弱化展示 |
| `deleted_at != null` | 回收站项目 | 仅允许恢复 |
### 4.2 设定完整度检查

| 后端状态 | UI 展示 | 按钮策略 |
|---|---|---|
| `ready` | 可开始创作 | 主按钮正常可用 |
| `warning` | 可继续，但有提醒 | 主按钮可用，展示黄色提示 |
| `blocked` | 关键信息缺失 | 禁止进入批量生成流程 |
### 4.3 内容状态

| 后端状态 | UI 标签 | 默认动作 |
|---|---|---|
| `draft` | 草稿 | 保存、继续编辑、确认 |
| `approved` | 已确认 | 可查看、继续编辑、进入下游 |
| `stale` | 已失效 | 明确警告，可编辑或重生成 |
| `archived` | 已归档 | 默认隐藏或折叠 |

补充：

- `Outline` 与 `OpeningPlan` 的主按钮固定为“保存草稿”与“确认”。
- `stale` 不是错误态，而是需要用户决策的警示态。
### 4.4 工作流状态

| 后端状态 | UI 标签 | 主动作 |
|---|---|---|
| `created` | 已创建 | 自动跳转加载或等待启动完成 |
| `running` | 运行中 | 可暂停、可取消 |
| `paused` | 已暂停 | 可恢复、可取消 |
| `failed` | 执行失败 | 显示错误原因，允许重看上下文 |
| `completed` | 已完成 | 允许导出和查看结果 |
| `cancelled` | 已取消 | 只读查看 |
### 4.5 暂停原因映射

| `pause_reason` | UI 说明 |
|---|---|
| `user_request` | 用户主动暂停 |
| `user_interrupted` | 用户中断当前生成 |
| `budget_exceeded` | 预算触发暂停 |
| `review_failed` | 审核未通过，等待处理 |
| `error` | 运行时错误暂停 |
| `loop_pause` | 到达阶段暂停点 |
| `max_chapters_reached` | 达到章节上限 |
### 4.6 章节任务状态

| 原始状态 | UI 标签 | 说明 |
|---|---|---|
| `pending` | 未开始 | 尚未执行 |
| `generating` + `content_id is null` | 生成中 | 当前任务正在推进 |
| `generating` + `content_id exists` | 待确认 | 草稿已生成，等待用户确认 |
| `completed` | 已确认 | 已形成当前工作流可用正文 |
| `failed` | 失败 | 需要查看原因或修正 |
| `skipped` | 已跳过 | 不阻塞后续导出 |
| `stale` | 已失效 | 需重新执行 `chapter_split` |
| `interrupted` | 已中断 | 当前任务被中途打断 |

关键规则：

- 前端不能把原始 `generating` 一律翻译成“生成中”。必须结合 `content_id` 区分“运行中”和“待确认”。
- `stale` 章节任务不是普通警告；它意味着当前计划已经不可信，必须引导用户回到任务重建。
### 4.7 导出状态口径

| UI 概念 | 当前口径 |
|---|---|
| 可选格式 | `txt`、`markdown` |
| 导出入口 | 仅从某次 `workflow` 发起 |
| 导出列表 | 按 `project` 查看历史导出 |
| 章节状态展示 | 前端用统一文案展示，不自行拼多表逻辑 |

补充：

- `approved` 和 `stale` 正文都可能进入导出，但 `stale` 必须有 warning。
- 导出前如遇 `pending / generating / interrupted / failed` 章节，必须阻止导出并展示明确原因。
---
## 5. 分视图交互规则
### 5.1 Auth

- 单页双态即可：登录、注册。
- 不出现“忘记密码”“短信登录”等未落地流程。
- 登录成功后直接进入 `Lobby`。
### 5.2 Lobby / Incubator

- 新建项目流程：基础信息 -> 项目设定 -> 完整度检查 -> 进入 `Studio`。
- 删除项目只进入回收站，不弹出永久删除二次流程。
- 回收站仅提供恢复按钮。
- 全局设置中的 `Credential Center` 支持用户级与项目级凭证管理、验证与启停。
### 5.3 Studio

- `ProjectSetting`、`Outline`、`OpeningPlan`、`Chapter` 使用同一套左侧结构导航。
- 用户修改正文时可以做节流自动保存，但失败必须显式提示，不能静默吞掉。
- 版本面板支持：
  - 查看版本列表
  - 回滚到某版本
  - 标记 / 取消最佳版本
- `Review & Diff` 在 `Studio` 只保留“跳转到当前 workflow 审核面板”的联动，不直接内嵌完整审核数据面板。
### 5.4 Engine

- 工作流启动前，先展示设定完整度与前置资产状态。
- `mode=manual|auto` 只做状态展示，不提供运行时切换。
- `pause / resume / cancel` 使用显式按钮，不做隐式自动切换。
- 章节任务重建必须明确告知会覆盖当前计划。
- `logs / reviews / billing / context / replays` 统一收在右侧详情区或二级 tab，不再拆成多个页面。
### 5.5 Lab

- 默认入口是分析记录列表，不是上传面板。
- 新建分析使用结构化表单，写入 `analysis_type`、`source_title`、`result`、`suggestions`。
- `generated_skill_key` 当前只作为只读结果字段展示。
### 5.6 Export Dialog

- 发起导出前先选择格式。
- 只显示 `txt` 与 `markdown`。
- 下载入口来自项目导出列表，不额外造一套下载中心。
---
## 6. 响应式规则
### 6.1 断点

| 断点 | 说明 |
|---|---|
| `>= 1440px` | 完整桌面工作台 |
| `1024px - 1439px` | 标准桌面，允许三栏压缩 |
| `768px - 1023px` | 平板，右侧详情面板改抽屉 |
| `< 768px` | 手机，仅保留浏览与轻操作 |
### 6.2 各主视图策略

| 视图 | 桌面 | 平板 | 手机 |
|---|---|---|---|
| `Lobby` | 卡片墙 + 侧栏 | 双列卡片 | 单列卡片 |
| `Studio` | 三栏 | 两栏 + 抽屉 | 章节列表与编辑分步进入 |
| `Engine` | 概览 + 任务 + 详情 | 概览 / 详情分 tab | 只提供状态浏览，不做复杂编排 |
| `Lab` | 列表 + 详情 + 新建 | 列表 / 详情切换 | 列表优先，详情单独进入 |

补充：

- 手机端不承担复杂工作流编排和多面板并排操作。
- 任何断点下都不能隐藏关键状态提示和主动作。
---
## 7. 无障碍与可用性规则

- 所有状态颜色必须配套文字标签和图标。
- 焦点态必须清晰可见，不能只靠浏览器默认样式。
- 所有抽屉、对话框都要支持 `Esc` 关闭和焦点回收。
- 键盘可完成主流程：切换 tab、打开版本面板、保存、确认、暂停、恢复、导出。
- SSE 日志区域必须使用可朗读的 `aria-live` 区域，但默认不要过度打断。
- 开启 `prefers-reduced-motion` 时，所有过渡动画降为淡入淡出。
---
## 8. 边界态规则
### 8.1 空态

| 场景 | 空态文案方向 |
|---|---|
| 无项目 | 引导新建项目 |
| 无大纲 / 无开篇设计 | 引导先完成前置资产 |
| 无章节 | 引导先重建章节任务或启动工作流 |
| 无分析结果 | 引导新建第一条分析记录 |
| 无导出记录 | 引导从已完成工作流发起导出 |
### 8.2 加载态

- 列表用骨架屏。
- 详情区保留布局骨架，避免整页闪烁。
- 长耗时动作必须显示“处理中”而不是只禁用按钮。
### 8.3 错误态

- API 错误必须展示明确失败原因。
- `404` 类 owner 隔离错误统一展示为“资源不存在或无权访问”。
- 自动保存失败必须弹出可感知提示，不能静默失败。
### 8.4 长连接与重连

- `events` SSE 断开时，在 `Engine` 顶部展示“实时连接已断开，正在重试”。
- 重连成功后收起提示并追加一条系统事件。
- 如果工作流已进入终态，则停止自动重连。
### 8.5 禁用态

- 未通过设定完整度检查时，禁用启动工作流。
- 前置资产未确认时，禁用章节任务重建。
- 当前没有可用 `workflow_id` 时，禁用导出入口。
---

*文档版本：2.0.0*  
*更新说明：将 UI 交互补充收口为当前后端对齐版，新增能力矩阵、状态映射、响应式、无障碍与边界态规则。*
