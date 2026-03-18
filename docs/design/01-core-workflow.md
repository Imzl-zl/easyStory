# 核心工作流设计

| 字段 | 内容 |
|---|---|
| 文档类型 | 功能设计 |
| 优先级 | 🔴 MVP 必须 |
| 关联文档 | [上下文注入](./02-context-injection.md)、[审核精修](./03-review-and-fix.md)、[章节生成](./04-chapter-generation.md) |

---

## 1. 概述

核心工作流包括：节点系统、双工作模式（手动/自动）、工作流状态机、并发控制、可视化监控、配置资源管理。

**核心设计原则：**
- **平台思维**：不预设固定流程，用户自定义节点和流程
- **灵活性优先**：支持从简单到复杂的各种使用场景
- **渐进式复杂度**：新手可以快速上手，高级用户可以深度定制

---

## 2. 节点系统

### 2.1 核心理念

**平台思维：用户自定义流程。** 系统不预设固定的创作流程，而是提供节点系统，让用户根据需求自由组合。

### 2.2 节点定义

每个节点代表一个创作步骤：

| 配置项 | 说明 | 必填 |
|-------|------|------|
| `id` | 节点唯一标识 | ✅ |
| `name` | 节点名称 | ✅ |
| `type` | 节点类型（generate/review/export） | ✅ |
| `skill` | 关联的 Skill ID | ❌ |
| `hooks` | 关联的 Hooks | ❌ |
| `reviewers` | 审核 Agents 列表 | ❌ |
| `auto_proceed` | 是否自动进入下一节点 | ❌ |
| `auto_review` | 是否自动审核 | ❌ |
| `auto_fix` | 审核失败是否自动精修 | ❌ |

> MVP 节点类型仅支持 `generate`、`review`、`export`。`custom` 类型预留，计划 v0.2 实现。

### 2.3 节点配置示例

```yaml
- id: "outline"
  name: "生成大纲"
  type: "generate"
  skill: "skill.outline.xuanhuan"
  hooks:
    after:
      - "hook.auto_save"
  auto_review: true
  reviewers:
    - "agent.consistency_checker"
  auto_proceed: false  # 需要人工确认
```

### 2.4 Skill 的作用

**Skill = 可复用的提示词模板**

- **有 Skill 配置**：每次执行节点时，自动使用 Skill 的提示词模板
- **没有 Skill 配置**：用户每次手动输入 Prompt

### 2.5 节点创建方式

**混合界面（兼顾不同用户群体）：**

1. **表单式配置界面**（新手友好）— 逐步添加，实时预览 YAML
2. **YAML 编辑模式**（高级用户）— 直接编辑，语法高亮
3. **两种方式实时同步** — 表单修改 ↔ 自动更新 YAML

---

## 3. 双工作模式

### 3.1 设计理念

**工作流级默认 + 节点级覆盖**

| 模式 | 适用场景 | 特点 |
|------|---------|------|
| 手动模式 | 精细打磨、实验性创作 | 每步需人工确认 |
| 自动模式 | 批量生产、成熟流程 | 自动审核+精修+推进 |

### 3.2 手动模式

```yaml
workflow:
  mode: "manual"
  settings:
    auto_proceed: false
    auto_review: false
```

用户操作：生成 → 查看/编辑/对话修改 → 手动审核（可选） → 确认 → 下一节点

**手动模式交互细节：**

| 阶段 | 用户可执行的操作 | 说明 |
|------|----------------|------|
| 生成完成后 | 查看生成内容 | 内容以草稿状态展示在编辑器中 |
| | 编辑内容 | 直接在编辑器中修改，自动保存草稿（每 30 秒） |
| | AI 对话修改 | 通过侧边栏对话让 AI 修改特定部分 |
| | 手动触发审核 | 可选操作，点击"审核"按钮运行配置的 Reviewer |
| | 查看审核结果 | 查看各 Reviewer 的评分和问题列表 |
| 确认操作 | 点击"确认并继续" | 创建正式版本（ContentVersion）、触发事实抽取、推进到下一节点 |

**确认动作的前置条件：**
- 内容不为空
- 无正在进行的 AI 修改操作

**离开与恢复：**
- 用户可随时离开页面，状态保持为 `paused`
- 无超时限制，下次回来时从上次位置继续
- 草稿自动保存，不会丢失编辑内容

### 3.3 自动模式

```yaml
workflow:
  mode: "auto"
  settings:
    auto_proceed: true
    auto_review: true
    auto_fix: true
  safety:
    max_fix_attempts: 3
```

流程：生成 → 自动审核 → 通过则自动下一步 / 失败则自动精修（最多 `max_fix_attempts` 次） → 仍失败则暂停等人工

### 3.4 节点级覆盖

```yaml
workflow:
  mode: "auto"  # 默认自动模式

  nodes:
    - id: "outline"
      auto_proceed: false  # 大纲节点强制人工确认

    # 章节生成通常是一个循环节点（而不是每章一个节点）
    # “混合体验”（例如每 10 章暂停一次）用 loop.pause 表达，而不是增加 mode=hybrid
    - id: "chapter_gen"
      loop:
        pause:
          strategy: "every_n"
          every_n: 10
```

### 3.5 运行时切换

支持执行过程中动态切换：自动→手动（随时暂停） / 手动→自动（从当前位置开始自动）。切换时保持当前节点状态。

---

## 4. 工作流状态机

### 4.0 LangGraph 与 StateMachine 的分工

**LangGraph** 负责**节点编排**：通过 StateGraph 定义节点执行顺序和条件分支（如审核通过→下一节点 / 失败→精修），是工作流的"调度器"。

**WorkflowStateMachine** 负责**业务状态管理**：维护 WorkflowExecution 的生命周期状态（created/running/paused/completed/failed/cancelled），处理暂停恢复、并发控制、预算检查等业务逻辑。

两者关系：WorkflowStateMachine 控制"何时启动/暂停/恢复"，LangGraph 控制"运行时节点怎么走"。LangGraph 不管理 WorkflowExecution 的持久化状态，StateMachine 不干预节点间的路由逻辑。

### 4.1 状态转换图

```
created   --start()--------------------> running
running   --pause()--------------------> paused
running   --all nodes done-------------> completed
running   --unrecoverable error-------> failed
running   --cancel()-------------------> cancelled
paused    --resume()-------------------> running
paused    --cancel()-------------------> cancelled
failed    --retry()--------------------> running
```

**合法状态转换：**

| 当前状态 | 可转换到 | 触发方式 |
|---------|---------|---------|
| created | running | start() |
| running | paused, completed, failed, cancelled | pause()/完成/错误/cancel() |
| paused | running, cancelled | resume()/cancel() |
| failed | running | retry()（受安全阀约束） |
| completed | —（终态） | — |
| cancelled | —（终态） | — |

> `failed → running`（retry）在业务上允许，但必须通过安全阀校验（如 `workflow.safety.max_total_retries`），否则会被拒绝并要求人工介入（见 [成本控制](./08-cost-and-safety.md)）。

### 4.2 用户动作语义

**MVP 必须区分三个容易混淆的动作：**

| 动作 | 作用层级 | 结果 |
|------|---------|------|
| 停止当前生成 | 节点级 | 尝试中断当前流式 LLM 调用；当前 `NodeExecution` 标记为 `interrupted`；`WorkflowExecution` 进入 `paused`，`pause_reason="user_interrupted"` |
| 暂停工作流 | 工作流级 | 若当前没有流式生成，直接 `running -> paused`；若正在生成，则先执行“停止当前生成”，再进入 `paused` |
| 取消工作流 | 工作流级终止 | 允许从 `running` 或 `paused` 发起；`running` 时先尽力中断当前节点，再进入 `cancelled`，之后不可恢复 |

**设计原则：**
- “停止当前生成”不是”取消工作流”，它只是把当前节点拉回人工决策点
- “暂停工作流”用于暂时中止自动推进，后续允许恢复
- “取消工作流”是放弃本次执行，不保留继续执行语义

### 4.3 paused 状态的统一语义

`paused` 是**工作流执行层面的唯一暂停态**，覆盖以下所有场景：

| pause_reason | 触发方式 | 说明 |
|-------------|---------|------|
| `user_request` | 用户点击”暂停” | 用户主动暂停自动推进 |
| `user_interrupted` | 用户点击”停止当前生成” | 中断流式生成后进入暂停 |
| `budget_exceeded` | 预算超限 | 系统自动暂停 |
| `review_failed` | 精修达上限 | on_fix_fail=pause 时触发 |
| `error` | 不可恢复错误 | 需人工介入 |
| `loop_pause` | loop.pause 策略触发 | 每 N 章暂停检查 |
| （无，手动模式节点间）| 节点完成等待确认 | 手动模式每步都经历”运行→暂停→确认→运行” |

**关键约束：** 同一项目存在 `running` 或 `paused` 状态的工作流时，禁止启动新工作流。这意味着手动模式下用户离开页面（工作流处于 `paused`）后，必须先 resume 当前工作流或 cancel 它，才能启动新的。这是预期行为，不是限制。

### 4.4 暂停/恢复机制

暂停时保存运行时快照到 `WorkflowExecution.snapshot`，包含以下信息：

| 快照内容 | 说明 |
|---------|------|
| 当前节点 ID 与执行 ID | 恢复时知道从哪继续 |
| 当前执行序号 | 章节循环的进度 |
| 恢复上下文 | 如章节任务 ID、章节号 |
| 已完成节点列表 | 各节点完成状态 |
| 待处理动作 | 如用户决策请求 |
| 部分产物 | 中断时已生成的部分内容 |

> `snapshot` 是**运行时快照**，用于恢复执行；不同于启动时不可变的 `workflow_snapshot/skills_snapshot/agents_snapshot`。
>
> → 数据模型详见 [数据库设计](../specs/database-design.md) § WorkflowExecution

---

## 5. 并发控制

### 5.1 单项目单工作流

**同一项目不允许多个工作流并行运行。** 启动工作流时检查是否有 running/paused 状态的执行，有则拒绝。

### 5.2 用户编辑与工作流并发

**原则：工作流读取上下文时做快照，不受后续编辑影响。**

节点执行前，系统构建当前上下文并计算 SHA-256 哈希值，作为该节点的输入快照。后续用户编辑不影响正在执行的节点。

> → 上下文构建详见 [上下文注入](./02-context-injection.md)

- 用户可以随时编辑任何章节
- 工作流使用的是快照，不受影响
- 编辑完成后，下游章节标记为 stale（详见 [05-content-editor](./05-content-editor.md)）

---

## 6. 工作流可视化（MVP 简化版）

### 6.1 MVP 范围：列表视图

```
工作流执行监控:
  ├─ [大纲] ✅ 已完成 (2分钟前)
  ├─ [第1章] 🔄 执行中 (生成内容...)
  ├─ [第2章] ⏸️ 等待中
  └─ [第3章] ⏸️ 等待中
```

实时信息：节点状态、执行时间、Token 消耗、审核结果

### 6.2 实时推送（SSE）

使用 SSE（Server-Sent Events）实时推送节点状态变更，包括节点启动、完成、错误等事件。

> **决策**：使用 SSE 而非 WebSocket，与 tech-stack 决策一致。

### 6.3 不做的功能（留到第二阶段）

- ⬜ 拖拽式图形化编排
- ⬜ 复杂的流程图展示
- ⬜ 节点连线和依赖可视化

---

## 7. 配置资源管理

### 7.1 目录结构

```
/config/
├── skills/          # Skills 配置
│   ├── outline/
│   └── chapter/
├── agents/          # Agents 配置
│   ├── writers/
│   └── reviewers/
├── hooks/           # Hooks 配置
└── workflows/       # Workflows 配置
```

### 7.2 管理方式

- 用户通过 Web UI 创建/编辑配置
- 配置自动保存为 YAML 文件
- 支持 Git 版本管理
- 支持导入/导出配置文件（分享给他人）

---

*最后更新: 2026-03-17*
