# easyStory 功能设计索引

| 字段 | 内容 |
|---|---|
| 文档类型 | 设计索引 |
| 文档状态 | 生效 |
| 创建时间 | 2026-03-16 |

---

## 文档阅读指南

本目录包含 easyStory 的完整功能设计文档，按模块拆分为 18 个独立文件。

**建议阅读顺序：**
1. 先读 `01-core-workflow` 理解核心架构
2. 再读 `02-context-injection` 和 `03-review-and-fix` 理解生成质量保障
3. 其余按需查阅

---

## 模块总览

| 编号 | 模块 | 文件 | 优先级 | 说明 |
|------|------|------|--------|------|
| 01 | 核心工作流 | [01-core-workflow](./01-core-workflow.md) | 🔴 | 节点系统 + 双模式 + 状态机 |
| 02 | 上下文注入 | [02-context-injection](./02-context-injection.md) | 🔴 | 三层优先级 + Story Bible + 裁剪 |
| 03 | 审核精修 | [03-review-and-fix](./03-review-and-fix.md) | 🔴 | ReviewResult Schema + 聚合规则 + 精修策略 |
| 04 | 章节生成 | [04-chapter-generation](./04-chapter-generation.md) | 🔴 | 循环 + 拆分 + 执行绑定 + 恢复 |
| 05 | 内容编辑 | [05-content-editor](./05-content-editor.md) | 🔴 | 编辑器 + 版本管理 + 下游影响 |
| 06 | 创作设定 | [06-creative-setup](./06-creative-setup.md) | 🔴 | 对话式设定 + 结构化输出 + 启动检查 |
| 07 | 小说分析 | [07-novel-analysis](./07-novel-analysis.md) | 🟡 | 上传 + 采样 + 分析 + Skill 生成 |
| 08 | 成本控制 | [08-cost-and-safety](./08-cost-and-safety.md) | 🔴 | 预算 + 安全阀 + Dry-run + Token 统一 |
| 09 | 错误处理 | [09-error-handling](./09-error-handling.md) | 🔴 | 分类 + 重试 + 模型降级 |
| 10 | 用户认证 | [10-user-and-credentials](./10-user-and-credentials.md) | 🔴 | User 模型 + 凭证管理 + 权限 |
| 11 | 导出 | [11-export](./11-export.md) | 🟡 | 格式 + 范围 + 最佳版本选择 |
| 12 | 流式输出 | [12-streaming-and-interrupt](./12-streaming-and-interrupt.md) | 🟡 | SSE + 中途打断 + 停止/暂停语义 |
| 13 | AI 偏好学习 | [13-ai-preference-learning](./13-ai-preference-learning.md) | 🟡 | 记忆系统 + 编辑模式分析 + 注入治理 |
| 14 | 伏笔追踪 | [14-foreshadowing-tracking](./14-foreshadowing-tracking.md) | 🟡 | 生命周期 + 自动检测 + 提醒注入预算 |
| 15 | 写作面板 | [15-writing-dashboard](./15-writing-dashboard.md) | 🟡 | 指标 + 趋势 + 导出 |
| 16 | MCP 预留 | [16-mcp-architecture](./16-mcp-architecture.md) | 🔴 | 三方向 + 抽象层 + 架构约束 |
| 17 | 跨模块契约 | [17-cross-module-contracts](./17-cross-module-contracts.md) | 🔴 | 并发幂等 + 模板安全 + 级联删除 |
| 18 | 数据备份 | [18-data-backup](./18-data-backup.md) | 🟡 | 软删除 + 回收站 + 执行日志 |

---

## 实施优先级总结

### MVP 必须实现（🔴）— 共 30 项

**功能模块（11 项）：**

1. 成本控制与安全阀 — 防止 token 失控
2. 错误处理与容错 — 保证稳定性
3. 工作流状态机完善 — 支持暂停/恢复/取消
4. 多用户基础隔离 — 预留扩展性
5. 配置版本管理 — 历史可追溯
6. 内容编辑器 — 用户使用频率最高的功能
7. 精修机制详细设计 — 定义精修输入/策略/Skill 来源
8. 对话式设定输出定义 — 结构化输出 + 变量映射
9. 章节循环生成机制 — 大纲拆分 + 中断恢复 + 跳过
10. Skill/Workflow Schema 静态校验 — 启动前编译校验
11. 模型供应商凭证管理 — Key 加密存储 + 作用域

**跨模块契约（6 项）：**

12. 审核结果结构化 Schema — ReviewResult/ReviewIssue 统一契约
13. Story Bible 版本绑定 — 事实绑定 source_content_version_id
14. 并发/幂等语义 — 状态机 + FOR UPDATE 锁 + 唯一约束
15. Token 计数单一来源 — TokenCounter + ModelPricing 统一类
16. 模板渲染安全边界 — SandboxedEnvironment + 白名单 filter
17. 数据留存级联策略 — 统一删除服务 + 留存时间规则

**功能逻辑规格：**

重点包括：上下文→Skill 变量映射、编辑旧章节下游处理、审核聚合规则、精修重新审核范围、运行中停止语义、ChapterTask 执行绑定、设定完整度检查、动态章节终止、上下文裁剪算法、导出最佳版本策略、体验型上下文预算等。

### MVP 建议简化实现（🟡）— 12 项

> **Story Bible 说明**：🔴 的"Story Bible 版本绑定"指数据模型层的结构预留（`source_content_version_id` 字段和冲突标记机制），这是上线阻塞项。🟡 的"Story Bible"指完整的事实自动抽取和注入能力，MVP 可简化为手动录入或基础规则抽取。

31–42. 内容导出、数据备份、执行日志、小说分析优化、Story Bible 完整能力、上下文可观测性、Dry-run预估、Prompt回放、流式输出+打断、AI偏好学习、伏笔追踪、写作数据面板

### 第二阶段（🟢）

43–45. 批量操作/A/B测试/协作/审核、MCP Client、MCP Server

---

## 验收标准

> 验收标准按优先级分层。🔴 项全部通过是上线阻塞条件；🟡 项建议简化实现但不阻塞上线。

### 🔴 MVP 上线阻塞 — 功能验收

- [ ] 用户可以注册/登录
- [ ] 创建项目时自动关联到当前用户
- [ ] 工作流执行时记录 token 消耗
- [ ] 超过预算时自动暂停并通知用户
- [ ] 项目级和用户级日预算可同时生效，防止通过多项目绕过预算
- [ ] LLM 调用失败时自动重试（最多 3 次）
- [ ] 模型降级前会按 Skill/Agent/Node 的 `required_capabilities` 过滤不兼容模型
- [ ] 工作流可以暂停/恢复/取消
- [ ] 每次执行保存配置快照
- [ ] 内容编辑器支持 Markdown 编辑 + AI 辅助修改
- [ ] 编辑后自动创建新版本
- [ ] 审核失败时精修策略按问题数量自动选择（局部/整篇）
- [ ] 对话设定产出结构化设定文档
- [ ] 用户可以跳过对话直接填写设定
- [ ] 大纲生成后自动拆分章节任务列表
- [ ] 章节生成失败时可暂停/跳过/重试
- [ ] 不同节点可以配置不同模型
- [ ] 工作流启动前 Schema 静态校验
- [ ] 模型 API Key 加密存储，支持三级作用域
- [ ] 添加 Key 后自动测试连通性

### 🔴 MVP 上线阻塞 — 契约验收

- [ ] 所有 Reviewer Agent 输出遵循 ReviewResult Schema
- [ ] ReviewIssue 包含 category、severity、location 定位
- [ ] StoryFact 绑定 source_content_version_id，修订时旧事实自动失效
- [ ] resume_workflow 幂等（重复调用不会重复生成）
- [ ] node_executions 有 (workflow_execution_id, node_id, sequence) 唯一约束
- [ ] 所有状态变更通过 WorkflowStateMachine
- [ ] token 计数统一使用 TokenCounter
- [ ] 费用计算统一使用 ModelPricing
- [ ] Skill 模板使用 SandboxedEnvironment 渲染
- [ ] 模板保存时通过语法校验 + 变量引用检查 + 试渲染
- [ ] 项目删除通过 ProjectDeletionService 统一处理
- [ ] 软删除不动关联表，物理删除按依赖顺序级联清理

### 🔴 MVP 上线阻塞 — 功能逻辑验收

- [ ] ContextBuilder 输出变量 dict，通过 Jinja2 填充到 Skill 模板
- [ ] 未被 Skill 引用的注入类型不进入 Prompt，但在上下文报告中标记为 unused
- [ ] 第 1 章生成时，无数据的注入类型跳过并在上下文报告中标记 not_applicable
- [ ] 上下文超预算时按优先级裁剪，project_setting 永不裁剪
- [ ] 编辑旧章节后，下游章节标记为 stale
- [ ] 用户可选择忽略/重生成/逐章确认 stale 章节
- [ ] 审核聚合规则（pass_rule）可在节点级配置
- [ ] 精修后默认全部 reviewer 重跑
- [ ] 工作流执行时上下文使用快照，不受后续编辑影响
- [ ] 同一项目不允许同时运行两个工作流
- [ ] 运行中停止当前生成时，当前节点标记 interrupted，工作流进入 paused
- [ ] 大纲完成后由章节拆分 Skill 自动生成 ChapterTask 列表
- [ ] `chapter_split` 失败时禁止留下半套 ChapterTask，且不允许 skip
- [ ] ChapterTask 绑定 workflow_execution_id，恢复时只读取当前执行的章节计划
- [ ] WorkflowExecution.snapshot 有最小恢复 schema，能支撑 interrupted/pause 场景恢复
- [ ] 设定修改后检测影响范围并提示用户
- [ ] 首次启动工作流前执行设定完整度检查，阻止缺少关键信息的批量生成

### 🔴 MVP 上线阻塞 — MCP 架构预留验收

- [ ] Agent 通过 ToolProvider 抽象层调用 LLM
- [ ] Hook 通过 PluginRegistry 执行
- [ ] Service 层入参/返回用 DTO
- [ ] API Router 不直接操作数据库
- [ ] 认证在入口层处理
- [ ] Agent 配置预留 mcp_servers 字段
- [ ] Hook 配置 action.type 支持扩展

### 🔴 MVP 上线阻塞 — 性能与安全验收

- [ ] 单节点超时 5 分钟自动失败
- [ ] 工作流超时 1 小时自动失败
- [ ] 所有 API 需要认证
- [ ] 用户只能访问自己的项目
- [ ] 密码使用 bcrypt 加密
- [ ] JWT token 有效期 24 小时

### 🟡 MVP 建议简化 — 不阻塞上线

- [ ] 可以导出 TXT 和 Markdown 格式
- [ ] 删除项目后进入回收站（30 天内可恢复）
- [ ] 可以查看工作流执行日志
- [ ] 可以查看历史执行的配置版本
- [ ] Story Bible 事实库自动提取人物/地点/时间线
- [ ] 上下文构建报告可查看
- [ ] Dry-run 预估 token 消耗和费用
- [ ] Prompt/响应回放可查看（开关可控）
- [ ] 动态章节模式支持三种终止方式
- [ ] 设定修改影响结果分为自动替换 / 人工复核 / stale，并支持范围批量处理
- [ ] 小说上传支持 UTF-8 / GBK 编码自动检测
- [ ] StoryFact 新旧事实冲突时会标记 potential/confirmed conflict，而不是静默覆盖
- [ ] 章节检测失败时回退到固定长度切分
- [ ] `best` 导出策略依赖显式标记的最佳版本
- [ ] 回滚到旧版本时，StoryFact 同步回到对应版本视角
- [ ] `writing_preferences` 和 `foreshadowing_reminder` 受独立 token 上限约束
- [ ] 导出前预检章节状态，异常章节让用户选择处理方式
- [ ] 循环节点中 skipped 迭代算完成，不阻塞 export
- [ ] 日志查询 < 500ms
- [ ] 导出 10 万字 < 10 秒
- [ ] 生成过程中前端实时显示文字（SSE 流式）
- [ ] 用户可随时点击"停止"中断生成
- [ ] 中断后可选择保存/续写/重生成
- [ ] 系统自动分析用户编辑 diff
- [ ] 同类编辑 ≥3 次后归纳为长期偏好
- [ ] 偏好自动注入后续 Prompt
- [ ] 用户可查看/编辑/删除偏好
- [ ] 每章确认后自动检测伏笔
- [ ] major 伏笔超 20 章未提及标记为"可能遗忘"
- [ ] 生成时注入未解决伏笔提醒
- [ ] 数据面板展示字数趋势、Token 消耗、审核通过率
- [ ] AI 原稿保留率可追踪

---

## MVP 核心用户旅程

### 场景 1：新手快速开始

```
注册/登录
  → 选择"玄幻小说模板"
  → 填写基础设定（主角/世界观/核心冲突）
  → 系统创建项目并加载预配置 Workflow + Skills + Agents
  → 点击"开始创作"
  → 设定完整度检查（ready/warning/blocked）
  → 生成大纲 → 人工确认大纲
  → 自动拆分章节任务列表
  → 逐章生成（手动模式：每章生成后查看/编辑/确认）
  → 全部完成后导出 Markdown
```

### 场景 2：高级用户自定义流程

```
注册/登录
  → 创建空项目 → 对话式设定 或 手动填写结构化设定
  → 导入参考小说 → 分析文风 → 生成风格 Skill
  → 自定义 Workflow（YAML 编辑模式）
  → 配置多个审核 Agent（文风/违禁词/AI味/剧情一致性）
  → 自动模式批量生成，每 10 章暂停检查（loop.pause.every_n）
  → 暂停时编辑不满意的章节、调整后续章节任务
  → 恢复工作流继续生成
  → 导出 DOCX
```

### 场景 3：中断与恢复

```
自动生成进行中（第 25 章）
  → 用户点击"暂停工作流"
  → 查看已生成的 1-25 章内容
  → 修改第 20 章（保存新版本）
  → 系统标记第 21-25 章为 stale
  → 用户选择"重新生成 21-25 章"
  → 恢复工作流 → 从第 21 章继续
  → 完成后导出
```

---

## 多项目管理框架

### 项目隔离

- 每个项目通过 `owner_id` 关联到用户，用户只能访问自己的项目
- 项目间数据完全隔离（内容、工作流执行、token 消耗等）
- 同一项目不允许同时运行两个工作流

### 配置资源作用域

| 资源类型 | 作用域 | 说明 |
|---------|--------|------|
| Skill | global / project | global 所有项目可用，project 仅项目内可用 |
| Agent | global / project | 同上 |
| Hook | global | 全局可用 |
| Workflow | project | 绑定到具体项目 |

### 项目状态

```
draft → active → completed → archived
                              ↓ (删除)
                           回收站（30天）→ 物理删除
```

### 项目列表视图

- 按状态筛选（全部/进行中/已完成/已归档）
- 按更新时间排序
- 显示：项目名、题材、章节进度、最后更新时间

---

*最后更新: 2026-03-17*
