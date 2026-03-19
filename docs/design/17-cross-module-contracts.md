# 跨模块契约与不变量

| 字段 | 内容 |
|---|---|
| 文档类型 | 功能设计 |
| 优先级 | 🔴 MVP 必须钉死 |
| 关联文档 | [审核精修](./03-review-and-fix.md)、[成本控制](./08-cost-and-safety.md)、[数据备份](./18-data-backup.md) |

---

## 1. 概述

跨多个模块的接口契约和版本/并发语义。不提前定死，实现到一半必然出现模块对不上。

---

## 2. 并发幂等语义

### 2.1 幂等性规则

| 操作 | 幂等？ | 实现方式 |
|-----|--------|---------|
| `start_workflow` | 否 | 每次创建新 WorkflowExecution |
| `resume_workflow` | 是 | 已在 running 则忽略 |
| `pause_workflow` | 是 | 已在 paused 则忽略 |
| `interrupt_generation` | 是 | 当前节点不在流式生成中则忽略 |
| `cancel_workflow` | 是 | 已在 cancelled/completed 则忽略；running 时先尽力中断当前节点 |
| `retry_node` | 否 | 创建新的 NodeExecution，并分配新的 `sequence` |

### 2.2 防重复生成

`resume_workflow` 必须使用悲观锁（`FOR UPDATE`）获取 WorkflowExecution 记录：
- 若已在 `running` 状态 → 忽略（幂等）
- 若不在 `paused` 状态 → 抛出状态错误
- 否则 → 将状态更新为 `running`

### 2.3 唯一约束

```sql
ALTER TABLE node_executions
ADD CONSTRAINT uq_node_execution_unique
UNIQUE (workflow_execution_id, node_id, sequence);

ALTER TABLE chapter_tasks
ADD CONSTRAINT uq_chapter_task_plan
UNIQUE (workflow_execution_id, chapter_number);
```

**`sequence` 语义：**
- `sequence` 是**同一 `workflow_execution_id + node_id` 下的执行序号**
- 它用于区分首次执行、重试、手动重跑和循环迭代，不等同于业务上的 `chapter_number`
- 章节循环的逻辑身份由 `ChapterTask.chapter_number` 和 `NodeExecution.input_data.chapter_task_id/chapter_number` 共同标识

### 2.4 状态机

> → 合法状态转换详见 [核心工作流](./01-core-workflow.md) §4.1

### 2.5 中断语义

`interrupt_generation` 的行为：
1. 使用悲观锁获取 NodeExecution 记录
2. 若当前节点不在 `running_stream` 状态 → 忽略（幂等）
3. 将节点状态改为 `interrupted`
4. 将工作流状态改为 `paused`，`pause_reason` 设为 `user_interrupted`

**约束：**
- `interrupt_generation` 只负责把当前节点拉回人工决策点，不得直接把工作流标记为 `cancelled`
- `cancel_workflow` 允许从 `running` 或 `paused` 发起，但必须是显式用户动作
- 所有恢复逻辑都从 `paused` 继续，不从 `interrupted` 直接继续

---

## 3. Token 计数统一来源

> → TokenCounter 和 ModelPricing 的接口契约详见 [成本控制](./08-cost-and-safety.md) §6、§7

**使用约束：**

| 调用方 | 使用方法 | 场景 |
|--------|---------|------|
| BudgetGuard | count()（MVP 为估算） | 预算检查 |
| Dry-run | estimate()（快速） | 启动前预估 |
| ContextBuilder | count()（MVP 为估算） | 报告 token 占用 |
| TokenUsage 记录 | LLM API 返回值 | 最权威来源 |

价格配置：
```yaml
# config/model_pricing.yaml
models:
  claude-sonnet-4-20250514:   { input_per_1k: 0.003, output_per_1k: 0.015, context_window: 200000 }
  claude-opus-4-20250115:     { input_per_1k: 0.015, output_per_1k: 0.075, context_window: 200000 }
  gpt-4o:                     { input_per_1k: 0.005, output_per_1k: 0.015, context_window: 128000 }
  deepseek-v3:                { input_per_1k: 0.001, output_per_1k: 0.002, context_window: 128000 }
```

---

## 4. Prompt 模板渲染安全

### 4.1 使用 Jinja2 SandboxedEnvironment

Skill 模板渲染必须在沙箱环境中执行，使用 `StrictUndefined`（引用到的变量缺失必须抛错），只允许白名单 filter。

### 4.2 允许与禁止

| 能力 | 允许？ |
|-----|--------|
| `{{ var }}` 变量替换 | ✅ |
| `{% if %}` 条件 | ✅ |
| `{% for %}` 循环 | ✅ |
| 白名单 filter | ✅ |
| `{% macro %}` 宏 | ❌ |
| Import/Include | ❌ |
| `{{ obj.__class__ }}` | ❌ |

### 4.3 模板校验（保存时）

1. 语法正确性
2. 变量引用完整性（引用的变量是否在 inputs 中声明）
3. 沙箱安全性
4. 试渲染（用 mock 数据渲染一次）

### 4.4 变量解析与默认值（StrictUndefined 配套）

模板渲染使用 `StrictUndefined`，意味着：**模板里引用到的变量只要缺失，就必须抛错**。为避免不同模块各自补丁式“补变量”，统一定义变量合并顺序与校验规则。

**变量合并顺序（低 → 高优先级）：**

1. Skill `inputs/variables` 的 `default`（先预填充默认值）
2. 系统内置变量（如 `project.*`、`node.*`、`execution.*` 等元信息）
3. `ContextBuilder` 输出（如 `outline`、`story_bible`、`project_setting` 等）
4. 循环变量（如 `chapter_index`）
5. 节点级 `input_mapping` / 上游节点 `outputs` 映射结果
6. 用户手动覆盖（手动模式输入、编辑器“改 prompt 重试”等）

**渲染前校验：**

- 解析模板引用到的变量集合（Jinja2 meta），若引用变量未被合并产出且无默认值 → **编译失败**（禁止进入 LLM 调用）
- Schema 中 `required: true` 且无默认值的变量缺失 → **编译失败**
- 运行时渲染仍出现 undefined → **视为实现缺陷**，必须抛错并写入执行日志（禁止吞掉）

---

## 5. 数据留存级联策略

### 5.1 级联策略表

| 主表删除事件 | 关联表 | 策略 |
|------------|--------|------|
| Project 软删除 | 所有关联表 | 保留（回收站内可查） |
| Project 物理删除 | 所有关联表 | 级联物理删除 |
| User 删除 | Project | 转移或软删，不物理删 |

### 5.2 留存时间

```yaml
data_retention:
  soft_delete_retention_days: 30
  physical_delete_grace_days: 7
  prompt_replay_retention_days: 30
  execution_log_retention_days: 90
  token_usage_retention_days: 365
  cleanup:
    schedule: "0 3 * * *"
    batch_size: 100
    strategy: "oldest_first"
```

### 5.3 统一删除服务

ProjectDeletionService 提供三个操作：

| 操作 | 行为 |
|------|------|
| soft_delete | 只标记 `deleted_at`，关联数据不动 |
| restore | 清除 `deleted_at`，从回收站恢复 |
| physical_delete | 按依赖顺序级联物理删除所有关联数据 |

**MVP 边界：**
- 软删除 / 恢复只作用于 **Project aggregate**
- `Content`、`WorkflowExecution`、`Export`、`StoryFact` 等关联数据在项目进入回收站时继续保留，但不提供各自独立的“软删除/恢复”能力
- 只有 `physical_delete` 才按依赖顺序级联清理关联数据

---

## 6. 配置版本管理

### 6.1 配置快照

每次执行工作流时保存完整配置快照到 WorkflowExecution 中，包括 workflow_snapshot、skills_snapshot、agents_snapshot 三个不可变快照字段。

> → 数据模型详见 [数据库设计](../specs/database-design.md) § WorkflowExecution

### 6.2 运行中配置边界

同一次 `WorkflowExecution` 的执行边界必须固定：

- `start_workflow` 时绑定启动快照（`workflow_snapshot / skills_snapshot / agents_snapshot`）
- `resume_workflow` 只能按该快照恢复，**不得**读取用户暂停后改动的配置文件
- 用户在暂停期间修改 Workflow / Skill / Agent 配置，只影响**下一次新执行**
- 若用户希望“从第 N 章开始按新配置重跑”，系统应创建新的 `WorkflowExecution`，而不是在旧执行上热切换配置

### 6.2.1 配置快照 vs 上下文快照

这里必须区分两类“快照”，避免混淆：

- **配置快照（执行级）**：`workflow_snapshot / skills_snapshot / agents_snapshot`，在 `start_workflow` 时冻结，整个 `WorkflowExecution` 生命周期内不变
- **上下文快照（节点级）**：节点真正调用 LLM 前构建的输入上下文，按当时的项目数据生成，并记录到该节点/版本的溯源信息中

因此：

- 暂停后修改配置文件，不影响当前执行的 `resume`
- 节点一旦开始执行，其输入上下文不再受后续编辑影响
- 尚未开始的后续节点，会读取**当时最新的项目内容/设定数据**来生成自己的节点级上下文快照

### 6.3 配置文件版本化

```yaml
workflow:
  id: "workflow.xuanhuan_auto"
  version: "1.2.0"
  changelog:
    - version: "1.2.0"
      date: "2026-03-15"
      changes: "增加自动精修功能"
```

### 6.4 配置对比

```
GET /api/v1/workflows/{id}/diff?from=1.1.0&to=1.2.0
→ { "added": [...], "removed": [...], "modified": [...] }
```

---

## 7. 导出状态口径

### 7.1 单一业务状态

导出预检、导出列表和下载能力**不直接暴露** `Content`、`NodeExecution`、`ChapterTask` 的原始状态，而是通过统一的 `ExportChapterStateResolver` 归一化为以下业务状态：

- `completed`
- `draft`
- `failed`
- `skipped`
- `generating`

### 7.2 映射原则

- 当前章节存在活跃生成（如 `chapter_task.status=generating` 或节点仍在 `running/running_stream`）→ `generating`
- 当前章节被显式跳过 → `skipped`
- 存在可导出的当前内容，且内容状态为 `approved` 或 `stale` → `completed`
- 只有草稿/partial 内容，尚未形成可导出的正式版本 → `draft`
- 当前章节无可导出内容，且最近一次生成已失败 → `failed`

**约束：**
- `stale` 不是单独的导出状态；它属于 `completed`，但导出预检必须给出 warning
- UI 不得自行拼接多表状态判断，统一走同一套 Resolver 逻辑

---

*最后更新: 2026-03-19*
