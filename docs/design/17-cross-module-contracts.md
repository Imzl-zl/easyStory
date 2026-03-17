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

```python
async def resume_workflow(execution_id):
    async with db.begin():
        execution = await db.execute(
            select(WorkflowExecution)
            .where(WorkflowExecution.id == execution_id)
            .with_for_update()  # 悲观锁
        )
        if execution.status == "running": return  # 幂等
        if execution.status != "paused": raise InvalidStateError()
        execution.status = "running"
```

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

```python
class WorkflowStateMachine:
    VALID_TRANSITIONS = {
        "created":   ["running"],
        "running":   ["paused", "completed", "failed", "cancelled"],
        "paused":    ["running", "cancelled"],
        "failed":    ["running"],
        "completed": [],
        "cancelled": [],
    }
```

### 2.5 中断语义

```python
async def interrupt_generation(node_execution_id):
    node_execution = await lock_node_execution(node_execution_id)
    if node_execution.status != "running_stream":
        return  # 幂等

    node_execution.status = "interrupted"
    workflow = await lock_workflow_execution(node_execution.workflow_execution_id)
    workflow.status = "paused"
    workflow.pause_reason = "user_interrupted"
```

**约束：**
- `interrupt_generation` 只负责把当前节点拉回人工决策点，不得直接把工作流标记为 `cancelled`
- `cancel_workflow` 允许从 `running` 或 `paused` 发起，但必须是显式用户动作
- 所有恢复逻辑都从 `paused` 继续，不从 `interrupted` 直接继续

---

## 3. Token 计数统一来源

```python
class TokenCounter:
    """统一 Token 计数器，所有需要计数的地方必须调用此类"""
    def count(self, text, model) -> int:     # 精确（有 tokenizer 时）
    def estimate(self, text, model) -> int:  # 快速估算

class ModelPricing:
    """统一价格表，禁止 hardcode 价格"""
    def calculate_cost(self, model, input_tokens, output_tokens) -> float: ...
```

价格配置：
```yaml
# config/model_pricing.yaml
models:
  claude-sonnet-4-20250514:   { input_per_1k: 0.003, output_per_1k: 0.015, context_window: 200000 }
  claude-opus-4-20250115:     { input_per_1k: 0.015, output_per_1k: 0.075, context_window: 200000 }
  gpt-4o:                     { input_per_1k: 0.005, output_per_1k: 0.015, context_window: 128000 }
  deepseek-v3:                { input_per_1k: 0.001, output_per_1k: 0.002, context_window: 128000 }
```

**使用约束：**
- BudgetGuard 调 `count()` 做精确检查
- Dry-run 调 `estimate()` 做快速预估
- ContextBuilder 调 `count()` 报告占用
- TokenUsage 的数值来自 LLM API 返回值（最权威）
- ModelPricing 需要能热更新

---

## 4. Prompt 模板渲染安全

### 4.1 使用 Jinja2 SandboxedEnvironment

```python
class SkillTemplateRenderer:
    def __init__(self):
        self.env = SandboxedEnvironment(undefined=StrictUndefined)
        self.env.filters = {
            "truncate": self._safe_truncate,
            "upper": str.upper, "lower": str.lower,
            "trim": str.strip, "default": self._safe_default,
        }
```

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

```python
class ProjectDeletionService:
    async def soft_delete(self, project_id): ...     # 只标记 deleted_at
    async def restore(self, project_id): ...          # 清除 deleted_at
    async def physical_delete(self, project_id): ...  # 按依赖顺序级联
```

---

## 6. 配置版本管理

### 6.1 配置快照

每次执行工作流时保存完整配置：

```python
class WorkflowExecution:
    workflow_snapshot: Mapped[dict]   # 完整配置快照
    skills_snapshot: Mapped[dict]     # 所有 Skills 快照
    agents_snapshot: Mapped[dict]     # 所有 Agents 快照
```

### 6.2 配置文件版本化

```yaml
workflow:
  id: "workflow.xuanhuan_auto"
  version: "1.2.0"
  changelog:
    - version: "1.2.0"
      date: "2026-03-15"
      changes: "增加自动精修功能"
```

### 6.3 配置对比

```
GET /api/v1/workflows/{id}/diff?from=1.1.0&to=1.2.0
→ { "added": [...], "removed": [...], "modified": [...] }
```

---

*最后更新: 2026-03-17*
