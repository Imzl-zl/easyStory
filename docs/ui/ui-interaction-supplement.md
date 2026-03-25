# easyStory UI 交互补充规格（MVP 对齐版）

| 字段 | 内容 |
|---|---|
| 文档类型 | UI 交互规则与实施补充 |
| 文档状态 | 生效 |
| 创建时间 | 2026-03-16 |
| 最后更新 | 2026-03-25 |
| 关联文档 | [设计索引](../design/00-index.md)、[UI 白皮书](./ui-design.md)、[系统架构](../specs/architecture.md) |

> 本文档定义当前前后端联调阶段的交互真值：能力矩阵、状态映射、页面层级、响应式、无障碍和边界态。它不重写产品设计，只负责把当前可实施范围钉死。
---
## 1. 文档定位
### 1.1 本轮适用范围

- 优先服务当前后端已落地接口。
- 可以保留未来能力的视觉预留，但不得假装已经具备完整闭环。
- UI 如果需要表达设计预留，必须明确标注 `MVP UI 占位` 或 `Future`。
- 当前目标是大屏 Web 工作台，不引入桌面客户端专属语义。
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
| Template | `Lobby` / `Settings` | 模板列表、详情、创建、更新、删除 | `MVP 已支持` |
| Credential | 全局设置 | 用户/项目级凭证列表、创建、更新、删除、验证、启用、停用 | `MVP 已支持` |
| Analysis | `Lab` | 新建分析、列表、详情 | `MVP 已支持` |
| Review | `Engine` | 审核摘要、审核动作列表 | `MVP 已支持` |
| Billing | `Engine` | 工作流账单摘要、Token 使用明细 | `MVP 已支持` |
| Context | `Engine` | 上下文预览 | `MVP 已支持` |
| Observability | `Engine` | 节点执行、执行日志、SSE 事件流、Prompt 回放 | `MVP 已支持` |
| Audit | `Credential Center` / `Project Settings` | 项目审计日志、凭证审计日志 | `MVP 已支持` |
| Export | `Engine` | 项目导出列表、按工作流创建导出、下载导出文件 | `MVP 已支持` |
| Config Registry | `Lobby` | Skills/Agents/Hooks/Workflows 列表、详情、更新 | `MVP 已支持` |
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
      ?mode=template|chat|one-click
      ?step=1|2|3
    /config-registry
      ?type=skills|agents|hooks|workflows
      ?item=:configId
    /templates
      /:templateId
    /recycle-bin
    /settings
      ?tab=credentials
      ?sub=list|audit
      ?credential=:credentialId

  /workspace/project/:projectId/studio
    ?panel=setting|outline|opening-plan|chapter
    ?chapter=1
    ?versionPanel=1

  /workspace/project/:projectId/engine
    ?workflow=:workflowId
    ?tab=overview|tasks|reviews|billing|logs|context|replays
    ?execution=:executionId
    ?export=1

  /workspace/project/:projectId/lab
    ?analysis=:analysisId
    ?mode=list|create

  /workspace/project/:projectId/settings
    ?tab=audit
    ?event=:eventType
```

规则：

- `Lobby / Studio / Engine / Lab` 是主视图，不再新增同级页面。
- `Incubator / Recycle Bin / Export Dialog / Version Panel` 是子视图，不升级为一级路由主干。
- `Review & Diff` 属于 `Engine` 的 workflow 子视图；`Studio` 最多提供跳转入口，不直接承载审核数据面板。
- `Templates` 作为 `Lobby` 的子视图，支持列表和详情路由。
- `Audit Log` 只挂载在 `Credential Center` 的 `?sub=audit` 子视图和 `Project Settings` 的 `?tab=audit` 参数下。
- `Config Registry` 作为 `Lobby` 子视图，统一挂在 `/workspace/lobby/config-registry?type=skills|agents|hooks|workflows`。

### 3.1 物理表现层定义（Physical Container）

| 子视图 | 容器类型 | 交互理由 |
|---|---|---|
| `Incubator` | 全屏覆盖层 (Overlay) | 强调"开篇仪式感"，独立于书架状态 |
| `Recycle Bin` | 独立页面 (Page) | 属于管理流，需要完整的列表空间 |
| `Credential Center` | 设置页子项 (Settings View) | 属于全局配置，位于设置体系内 |
| `Template Library` | 独立页面 (Page) | 资产密集型，需要多列展示 |
| `Audit Log` | 独立页面 (Page) / 页面子视图 (Subview) | 项目级复用项目设置子页；凭证级挂在设置页内 |
| `Project Settings` | 独立页面 (Page) | 作为项目级子页承载设定与审计，不扩张顶层导航 |
| `Config Registry` | 独立页面 (Page) | 管理 Skills / Agents / Hooks / Workflows 的配置真值 |
| `Export Dialog` | 模态对话框 (Dialog) | 从工作流发起的轻量导出操作 |
| `Version Panel` | 侧抽屉 (Drawer) | 章节版本列表，折扇式开合 |

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
- 当前 `stale` 只使用一套视觉语言：墨迹褪色 + 警示标记，不做轻重分级。
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

#### 5.2.1 基础规则

- 新建项目流程：基础信息 -> 项目设定 -> 完整度检查 -> 进入 `Studio`。
- 删除项目只进入回收站，不弹出永久删除二次流程。
- 回收站仅提供恢复按钮。
- 全局设置中的 `Credential Center` 支持用户级与项目级凭证管理、验证与启停。

#### 5.2.2 Incubator 状态机

**状态流转：**

```text
SELECT_MODE -> INPUT -> PREVIEW -> VALIDATING -> SUCCESS
                  ^                    |
                  +---- ERROR <--------+
```

| 状态 | 说明 | UI 表现 |
|---|---|---|
| `SELECT_MODE` | 三选一：模板问答 / 自由对话 / 一键创建 | 全屏覆盖层，三个模式卡片 |
| `INPUT` | 表单填写 / 对话输入 | 触发"落墨"动效 |
| `PREVIEW` | 只读检查，展示生成的项目概览 | "宣纸卷轴"样式展示 |
| `VALIDATING` | 后端请求中 | 按钮变为"湿墨晕开"状态 |
| `SUCCESS` | 创建成功 | 播放"入纸"动效，1.5s 后自动跳转 `/project/:id/studio` |
| `ERROR` | 校验失败 | 返回 INPUT 态，保留已填写内容，顶部显示"红墨"报错 |

**模式切换逻辑：**

- 切换模式时，保留通用字段（项目名称、目标字数），清空模式特定输入（模板问答记录）。
- `PREVIEW` 态点击"创建"才触发 `VALIDATING`，不是 `INPUT` 态直接提交。

**失败处理：**

- 返回 `INPUT` 态，保留已填写内容。
- 顶部显示"红墨"报错提示，包含具体错误原因。
- 支持重试，不重置整个表单。

#### 5.2.3 Recycle Bin（回收站）

**核心逻辑：** 视觉差异、恢复仪式。

**视觉差异：**

- 枯墨感：卡片整体饱和度降低 40%，背景叠加明显的"破损宣纸"纹理。
- 边缘：卡片边框使用 1px 的虚线或不规则笔触，区别于普通项目的实线。

**信息密度：**

- 比普通列表更紧凑（Compact Mode）。
- 增加字段：删除时间。

**恢复逻辑：**

- 确认：弹出对话框"以此残卷续写前缘？（确认恢复该项目）"。
- 回流：恢复成功后，自动跳转回 Lobby 主列表。
- 高亮：对该恢复项进行一次"墨迹闪烁"高亮，提示其位置。

**空态文案：**

- "空无一物，残卷已清。"

### 5.3 Studio

- `ProjectSetting`、`Outline`、`OpeningPlan`、`Chapter` 使用同一套左侧结构导航。
- 用户修改正文时可以做节流自动保存，但失败必须显式提示，不能静默吞掉。
- 版本面板支持：
  - 查看版本列表
  - 回滚到某版本
  - 标记 / 取消最佳版本
- `Version Panel` 的展开只允许使用轻量折扇式开合，不做重 3D 连续旋转。
- `Review & Diff` 在 `Studio` 只保留"跳转到当前 workflow 审核面板"的联动，不直接内嵌完整审核数据面板。

#### 5.3.2 右侧辅助面板体系（Fan Panel System）

**核心逻辑：** 互斥展开、情境感知、动效一致。

**切换与互斥规则：**

- 互斥性：侧边栏同一时间仅允许一个面板展开。
- 点击新图标时，旧面板执行"折扇收拢"动效（150ms），新面板执行"折扇展开"动效（240ms）。
- 手动控制：右侧垂直图标栏（Icon Bar）作为固定锚点。

**面板类型：**

| 面板 | 功能 | 默认打开条件 |
|---|---|---|
| `Preparation Status` | 筹备态，展示设定完整度 | 项目初次进入或 ProjectSetting/Outline 处于 warning/blocked 状态 |
| `Stale Impact` | 失效分析，展示受影响章节 | 用户选中标记为 stale 的章节时自动切换至此 |
| `Review Jump` | 审核跳转，加载审核详情 | Engine 工作流因审核失败暂停时，点击顶部通知自动开启 |
| `Version Panel` | 版本历史 | 默认状态，当以上三个紧急状态均不存在时展示 |

**动效参数：**

- 收拢：150ms，`transform: scaleX(0)` + `opacity: 0`
- 展开：240ms，`transform: scaleX(1)` + `opacity: 1`
- 仅使用 `transform` 和 `opacity`，避免重排

### 5.4 Engine

#### 5.4.1 基础规则

- 工作流启动前，先展示设定完整度与前置资产状态。
- `mode=manual|auto` 只做状态展示，不提供运行时切换。
- `pause / resume / cancel` 使用显式按钮，不做隐式自动切换。
- 章节任务重建必须明确告知会覆盖当前计划。
- `logs / reviews / billing / context / replays` 统一收在右侧详情区或二级 tab，不再拆成多个页面。
- 节点状态反馈使用水墨语义：`running` 为湿墨晕层，`completed` 为入纸收锋，不使用持续呼吸灯。
- `Ink Pool` 或预算摘要的波纹只在 token usage / billing summary 更新时触发，不跟随每条日志滚动。

#### 5.4.2 运行态交互

**SSE 状态条：**

- 位于页面顶部，显示连接状态。
- 断开时显示"墨路中断，正在续接..."，背景为淡灰色噪点纹理。
- 重连成功后自动恢复正常状态显示。

**暂停展示：**

- 明确展示暂停原因（如 `review_failed`、`budget_exceeded`、`user_interrupted`）。
- 点击原因跳转至对应的 Tab（Review / Billing / Overview）。
- 暂停状态下，恢复按钮高亮显示。

**Workflow 未载入态：**

- 显示空态提示："尚未启动工作流，请先完成项目设定"。
- 提供"启动工作流"按钮入口。

#### 5.4.3 Prompt Replay 交互

- 必须先从时间轴选择一个 Execution Node。
- 中央区域才会浮现对应的 Prompt 对话过程。
- 支持折叠/展开 Prompt 内容。
- 显示 token 使用量和模型信息。
- 当前选中的 `execution` 需要同步到 URL 查询参数，刷新后可恢复。
- 若 URL 中的 `execution` 不属于当前 workflow，execution 列表加载完成后必须显式清理该参数。

#### 5.4.4 章节任务重建确认

- 弹窗显示："重建将覆盖当前章节计划，已生成的草稿将被标记为失效。"
- 需要二次确认才能执行。
- 重建后自动跳转至任务列表。
### 5.5 Lab

#### 5.5.1 基础规则

- 默认入口是左侧过滤器 + 列表，不是上传面板。
- 新建分析使用结构化表单，写入 `analysis_type`、`source_title`、`generated_skill_key`、`result`、`suggestions`。
- 删除动作只从详情区触发，必须先显式确认。
- 创建成功后，若新记录命中当前过滤器则自动选中；若未命中，则保留当前详情并给出顶部提示。

#### 5.5.2 筛选栏与布局

- Lab 使用三栏布局：左侧过滤器 + 列表，中央详情，右侧新建。
- 筛选栏位于左侧面板内部，不单独做 `sticky` 顶栏。
- 筛选维度：`analysis_type`、`content_id`、`generated_skill_key`。

#### 5.5.3 路由联动

- 当前 Lab 不做 URL query sync。
- 过滤条件与当前选中分析都只保留在页面本地状态。
- 刷新页面后回到服务端列表结果，并按当前列表默认选中规则恢复详情。

#### 5.5.4 反馈与选中

- 创建、删除、查询失败统一走页面顶部 feedback banner，只使用 `info / danger` 两种语义。
- 删除当前选中记录后，优先回退到列表中的下一条可用记录；若已是最后一条，则回退到上一条；若列表为空，详情区显式回到空态。
- 不为当前 MVP 增加额外的模式切换动效或 URL 驱动状态。
### 5.6 Export Dialog

#### 5.6.1 基础规则

- 发起导出前先选择格式。
- 只显示 `txt` 与 `markdown`。
- 下载入口来自项目导出列表，不额外造一套下载中心。

#### 5.6.2 导出前预检视图（Pre-check）

**逻辑：** 点击"导出"先进入预检层。

**阻断项（Blocking）：**

- 存在 `pending` 或 `failed` 状态的章节任务。
- 展示红墨 X，提示"正文残缺，无法成书"。
- 阻止导出，需先处理问题章节。

**警示项（Warning）：**

- 存在 `stale` 章节。
- 展示黄墨感叹号，提示"部分章节已失效，导出可能存在逻辑不一致"。
- 允许继续导出，但需确认。

#### 5.6.3 导出历史列表字段

| 字段 | 说明 |
|---|---|
| 文件名 | `Project_Name_WorkflowID_Date` 格式 |
| 格式 | TXT / Markdown |
| 体积 | 文件大小 |
| 完成时间 | 导出完成时间戳 |
| 下载按钮 | 下载入口 |

#### 5.6.4 异常态表现

| 状态 | UI 表现 |
|---|---|
| 下载中 | 按钮变为"墨滴连续滴落"动效 |
| 导出失败 | 列表项背景变为 `--bg-muted`，右侧显示红墨"重试"按钮 |
| 无记录 | "尚未付梓，暂无导出痕迹。" |

### 5.7 Template Library（模板库）

#### 5.7.1 基础规则

- 入口位置：`Lobby` 侧边栏或全局设置子视图。
- 列表视图：模板卡片列表，支持分类/标签筛选、搜索。
- 详情视图：模板预览，包含 Prompt 结构、参数定义、适用场景说明。
- 创建/编辑表单：YAML/JSON 编辑区 + Schema 校验反馈 + 参数定义表单。
- 删除确认：显示影响范围提示；如后端已返回引用数，则展示具体数量。
- 另存为模板：从 Studio 某次成功的 Prompt 配置保存为模板的交互路径。

#### 5.7.2 Built-in vs Custom 区分

| 类型 | 视觉标识 | 操作权限 |
|---|---|---|
| Built-in（内置） | 卡片左上角带"官方朱砂印章" | 仅支持"查看"和"基于此创建副本"，字段灰色只读 |
| Custom（自定义） | 无特殊标识 | 允许完整 CRUD |

**详情页字段展示：**

- 名称、描述、题材
- `workflow_id` 与节点数量
- `guided_questions`
- Prompt 结构（核心配置）与节点快照
- 创建/更新时间

补充：

- `关联模型建议`、`使用次数统计`、`作者信息` 当前不属于后端已提供字段，保留为 `Future` 展示预留。

#### 5.7.3 冲突与删除处理

**重名冲突：**

- 保存按钮禁用
- 输入框边框呈"红墨泼溅"纹理
- Tooltip 提示"此法度已存在"

**删除影响范围：**

- 若模板仍被项目或历史 workflow 执行引用，删除按钮禁用，并提示"模板仍被引用，不能删除"
- 仅对未被引用的自定义模板提供二次确认删除

### 5.8 Credential Center（凭证中心）

#### 5.8.1 基础规则

- 入口位置：全局设置 `/workspace/lobby/settings?tab=credentials`。
- 项目上下文入口：项目设置侧栏跳转到 `/workspace/lobby/settings?tab=credentials&scope=project&project=:projectId&sub=list`。
- 支持用户级与项目级凭证管理、验证、启用与停用。
- 删除需要二次确认；确认层只展示当前代码已支持的作用域优先级和回退规则，不伪造“肯定可删”的结论。
- `Audit Log` 子视图只负责查看凭证审计日志与切换审计目标；验证、启停、删除等状态变更动作只保留在 `list` 子视图。
- 当前 URL 语义：
  - `scope=user|project`
  - `project=:projectId` 用于保留当前项目上下文
  - `sub=list|audit`
  - `credential=:credentialId` 在 `list` 子视图表示当前编辑目标，在 `audit` 子视图表示当前审计目标

#### 5.8.2 作用域切换

- 顶部 Tab 切换"全局凭证"与"当前项目凭证"。
- 项目级凭证优先级高于全局凭证。
- 未提供项目上下文时，"当前项目凭证" Tab 禁用，只允许管理全局凭证。
- 当 create / update / verify / enable / disable / delete 任一 mutation 进行中时，`scope`、`sub` 与当前审计目标切换入口全部禁用，直到结果返回。

#### 5.8.3 覆盖提示

- 若当前项目已配置同 provider 的启用中项目级凭证，全局页面对应项显示"已被项目级重载"提示。
- 当前实现为 inline badge + 行内说明，并通过 `title` 补充具体项目级凭证名称；不额外引入 tooltip 系统。

#### 5.8.4 表单交互

| 字段 | 交互方式 |
|---|---|
| `provider` | 仅创建时可编辑；进入编辑态后只读展示，不支持直接修改 |
| `api_dialect` | 下拉框选择，选择后动态加载对应的 `base_url` 默认值 |
| `base_url` | 文本输入，根据 `api_dialect` 预填默认值 |
| `default_model` | 文本输入；当前更新接口不支持显式清空已有值 |
| `api_key` | 密码输入框，编辑态留空表示不轮换当前 key |

删除补充：

- 删除确认弹窗需要展示当前作用域、provider、启停状态，以及删除后的解析影响。
- 若凭证已有 token usage 历史，后端会拒绝删除；前端只显式提示这条规则，不静默改写删除结果。

#### 5.8.5 验证状态

| 状态 | UI 表现 |
|---|---|
| 动作进行中 | 当前目标按钮改为显式中文进行中文案：`验证中... / 启用中... / 停用中... / 删除中...`；当前 mutation 期间其余动作按钮保持禁用 |
| 验证成功 | 表单反馈区显示 `验证结果 + 最近验证时间`，时间格式统一为 UTC（例如 `03/25 06:08 UTC`） |
| 验证失败 | 表单反馈区显示后端返回的具体错误原因，不做静默降级 |

### 5.9 Audit Log（审计日志）

#### 5.9.1 基础规则

- 项目审计日志：挂载在 `Project Settings` 子页的 `?tab=audit` 子 Tab。
- 凭证审计日志：挂载在 `Settings -> Credential Center` 的 `?sub=audit` 子视图。
- 日志字段：时间戳、操作类型、操作人、目标资源、变更前后对比。
- 当前 MVP 筛选能力：按操作类型过滤；时间范围、操作人筛选待后端接口补齐后再加。
- 视觉风格：沿用 Engine 日志风格（JetBrains Mono），区分"系统行为"与"安全审计"的视觉密度。

#### 5.9.2 双入口视图

当前审计能力只定义两类入口：

| 类型 | 入口位置 | 容器类型 |
|---|---|---|
| Credential | `/workspace/lobby/settings?tab=credentials&sub=audit&credential=:credentialId` | 页面子视图 |
| Project | `/workspace/project/:projectId/settings?tab=audit` | 独立页面 (Page) |

补充：

- 当前没有“全局聚合审计”后端接口，不定义 `Global Audit` 总览页。

#### 5.9.3 Payload 处理

- 默认折叠，显示摘要信息。
- 点击"展开"时，模拟"信纸拆开"的 3D 动效。
- 展开后显示 JSON 详情或变更对比。

#### 5.9.4 对比视图

- 左右布局：左删（红墨淡化）、右增（浓墨实心）。
- 支持行级高亮差异。
- 长内容支持滚动，差异行自动定位。

### 5.10 Config Registry Admin（配置注册中心）

- 入口位置：`/workspace/lobby/config-registry`。
- 资产列表：四种资产（Skills / Agents / Hooks / Workflows）的 Tab 切换 + 卡片列表。
- 详情视图：元数据展示 + 原始 JSON DTO 预览。
- 编辑能力：完整 JSON DTO 编辑区；保存前先做前端 JSON 解析，字段校验仍以后端返回为准。
- 权限规则：不在前端静默推断管理员身份；401/403 必须直接展示后端错误。
- 实施标记：`MVP 已支持`。

### 5.11 Project Settings（项目设置子页）

#### 5.11.1 容器类型

- 当前 MVP 以独立页面 (Page) 实现，路径为 `/workspace/project/:projectId/settings`。
- 后续若改回 Drawer，不改变 `tab` 查询参数语义。

#### 5.11.2 入口差异

| 入口 | 侧重点 | Audit Tab | 特殊展示 |
|---|---|---|---|
| Lobby 进入 | 项目摘要、设定与项目审计 | 包含 | 项目卡片快捷入口 |
| Studio 进入 | 设定一致性 | 不走该子页 | 继续使用 `panel=setting` 的设定面板 |

补充：

- `/workspace/project/:projectId/settings?tab=audit` 主要服务 Lobby / 项目管理入口。
- `Studio` 内设定编辑继续走 `/workspace/project/:projectId/studio?panel=setting`，不把项目审计塞回 Studio 主编辑区。

#### 5.11.3 保存时机

- 当前 MVP 使用手动“保存设定”按钮。
- 完整度检查由用户显式触发，不做静默自动检查。
- 保存失败必须直接展示后端错误，不做 silent autosave。

#### 5.11.4 完整度检查卡片

- 固定显示在设定编辑区顶部。
- 展示当前设定完整度百分比。
- 缺失项以列表形式展示，点击可跳转对应编辑区。

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
| `Template Library` | 三列卡片 + 右侧详情侧板 | 双列卡片 + 抽屉详情 | 单列卡片，详情 Bottom Sheet |
| `Config Registry` | 双栏：配置树 + 编辑区 | 隐藏配置树，顶部导航 | 编辑器 readOnly，全屏编辑 |

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
- 背景纸纹必须保持静态和低对比度，不能影响正文可读性。
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
| 模板库为空 | "书案初设，尚无典籍。点击'创建模板'，为你的创作定下法度。" |
| 审计日志为空 | "雪地无痕，暂无往来行迹。待你落笔生花，此处自见功过。" |
| Config Registry 为空 | "机枢未发，灵窍尚待开启。" |

#### 8.1.1 页面级状态矩阵

| 页面 | 加载态（Skeleton） | 空态（Empty Copy） | 错误态（Error Copy） |
|---|---|---|---|
| Lobby | 书架格状骨架屏 | "空山新雨，静候佳作。点击新建开启创作。" | "书架倾颓（数据加载失败），请重整旗鼓（点击重试）。" |
| Studio | 中央编辑器长条骨架 | "案前无纸。请先在左侧选择章节或创建大纲。" | "墨路不通。当前内容无法载入。" |
| Engine | 执行节点动态波纹 | "机枢未发。请启动工作流以开始生成。" | "工作流受阻。错误代码：XXX。查看日志以排障。" |
| Lab | 列表与详情双栏骨架 | "暂无研究结论。新建分析以提取文风。" | "分析中断。无法读取结果。" |

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

### 8.6 Query 参数回退规则

| 参数 | 非法/无效处理 |
|---|---|
| `?tab` 非法 | 回退到第一个 Tab |
| `?workflow` 无效 | 回退到最近一次可访问的 workflow；若无可用 workflow，则回到未载入空态 |
| `?analysis` 无效 | 回到列表页 |
| `?chapter` 越界 | 回退到第一章或最后一章 |
| `?mode` 非法 | 回退到默认模式 |

### 8.7 禁用态文案（Tooltip Guide）

| 禁用动作 | Tooltip 文案 |
|---|---|
| 启动 Workflow | "设定尚未圆满，请先补齐项目设定。" |
| 重建章节任务 | "工作流运行中，不可更易计划。" |
| 导出入口 | "章节尚未确认，无墨可出。" |
| 删除内置模板 | "官方典籍，不可删改。" |
| 删除被引用模板 | "模板仍被引用，暂不可删除。" |

### 8.8 焦点流与键盘（A11y Flow）

- `Esc` 键：统一为"关闭当前最上层容器"（Drawer -> Dialog -> Overlay）。
- `Tab` 键焦点：
  - Incubator：焦点始终在表单输入框与"下一步"按钮间循环。
  - Audit Log：焦点在"折叠/展开"按钮上顺序移动。
  - Engine：焦点在 Tab 切换、主操作按钮、日志区域间移动。

---

*文档版本：2.4.1*  
*更新说明：收口 Audit 挂载点与 Settings 路由，明确 Config Registry 为 Future 预留，移除模板/导出/回收站中超出当前后端真值的字段与行为。*
