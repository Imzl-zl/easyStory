# 章节循环生成机制

| 字段 | 内容 |
|---|---|
| 文档类型 | 功能设计 |
| 优先级 | 🔴 MVP 必须 |
| 关联文档 | [核心工作流](./01-core-workflow.md)、[上下文注入](./02-context-injection.md) |

---

## 1. 概述

定义章节循环生成的完整机制：章节数量来源、大纲自动拆分、ChapterTask 数据模型、动态章节终止条件、中断恢复、循环节点完成语义。

---

## 2. 章节数量确定

```yaml
chapter_generation:
  source: "outline"              # 从大纲自动提取章节数
  # source: "manual"             # 用户手动指定
  # count: 50
  # source: "dynamic"            # 动态增长
  # max_chapters: 100
```

---

## 3. 大纲自动拆分章节任务

### 3.1 工作流中的位置

```yaml
nodes:
  - id: "outline"
    name: "生成大纲"
    skill: "skill.outline.xuanhuan"

  - id: "chapter_split"          # 章节拆分节点
    name: "拆分章节任务"
    skill: "skill.chapter_split"
    depends_on: ["outline"]

  - id: "chapter_gen"
    name: "生成章节"
    skill: "skill.chapter.xuanhuan"
    depends_on: ["chapter_split"]
    loop:
      enabled: true
      count_from: "chapter_split"
      item_var: "chapter_index"
```

### 3.2 拆分 Skill 输出 Schema

```yaml
skill:
  id: "skill.chapter_split"
  outputs:
    chapters:
      type: "array"
      items:
        type: "object"
        properties:
          number: { type: "integer" }
          title: { type: "string" }
          brief: { type: "string", description: "2-3 句话描述核心事件" }
          key_characters: { type: "array", items: { type: "string" } }
          key_events: { type: "array", items: { type: "string" } }
```

### 3.3 chapter_task 变量填充

循环生成时，系统从 `ChapterTask` 表读取对应章节的 `brief`，填充到 Skill 模板的 `{{ chapter_task }}`。

### 3.4 chapter_split → ChapterTask 写入机制

`chapter_split` 节点执行后，**引擎内置后处理**自动将 Skill 输出的 chapters 数组写入 `chapter_tasks` 表：

- **写入时机**: `chapter_split` 节点 status 变为 `completed` 时，由引擎自动触发（非 Hook，不可绕过）
- **字段映射**:

| Skill 输出字段 | chapter_tasks 表字段 |
|---------------|---------------------|
| `number` | `chapter_number` |
| `title` | `title` |
| `brief` | `brief` |
| `key_characters` | `key_characters`（JSONB） |
| `key_events` | `key_events`（JSONB） |

- 同时写入 `project_id`（从当前工作流上下文获取）和 `workflow_execution_id`（当前执行 ID）
- 所有新写入的 ChapterTask 初始 status 为 `pending`
- 若同一 `workflow_execution_id` 下已有 ChapterTask 记录，先清除旧记录再写入（幂等）

### 3.5 chapter_split 失败处理

`chapter_split` 是章节生成链路的硬前置依赖，因此失败时**不允许 skip**：

```yaml
- id: "chapter_split"
  on_fail: "pause"   # pause / fail
```

| 策略 | 行为 |
|------|------|
| `pause` | 工作流暂停，等待用户修大纲、重试拆分或手动录入章节计划（默认） |
| `fail` | 直接终止本次工作流 |

**约束：**
- `chapter_split` 输出校验失败时，必须整体回滚 `chapter_tasks` 写入，禁止留下半套章节计划
- downstream 的 `chapter_gen` 在 `chapter_split` 成功前不得启动
- 用户恢复时可选：
  - 重试 `chapter_split`
  - 修改大纲后重新执行 `outline -> chapter_split`
  - 手动导入/录入 ChapterTask 列表

---

## 4. ChapterTask 数据模型

ChapterTask 记录每个章节的任务信息，包括章节号、标题、摘要/任务描述（brief）、关键角色和事件列表、状态和关联的生成内容。

> → 数据模型详见 [数据库设计](../specs/database-design.md) § chapter_tasks

### 4.1 约束

- `ChapterTask` 必须绑定到具体 `workflow_execution_id`，不同执行的章节计划不得混用
- 唯一约束：`UNIQUE (workflow_execution_id, chapter_number)`
- 查询“当前执行的章节计划”时，必须显式按 `workflow_execution_id` 过滤
- `interrupted` 是非终态，只表示用户在生成过程中主动喊停，等待后续决策
- `NodeExecution.sequence` 是**同一 node 在当前 workflow_execution 下的执行序号**，不是 `chapter_number`
- 对章节循环来说，逻辑章节身份由 `ChapterTask.chapter_number` 和 `NodeExecution.input_data.chapter_task_id/chapter_number` 标识
- 同一章节的重试或“修改提示后重新生成”会创建新的 `NodeExecution`，但仍指向同一个 `chapter_task`

---

## 5. 动态章节终止条件

`source: "dynamic"` 模式下，三种终止信号任一触发即停止：

```yaml
chapter_generation:
  source: "dynamic"
  max_chapters: 100              # 硬上限
  termination:
    llm_signal:
      enabled: true
      marker: "[STORY_COMPLETE]" # LLM 输出含此标记则停止
    outline_completion:
      enabled: true              # 检查是否覆盖大纲结局
    manual_stop:
      enabled: true              # 用户随时可停
```

**循环行为：**
1. 从第 1 章开始，逐章生成
2. 每章生成后检查三种终止信号：LLM 输出标记 → 大纲覆盖度 → 用户手动停止
3. 检测到 `[STORY_COMPLETE]` 标记时，移除标记、保存内容、结束循环
4. 大纲所有结局要素都已覆盖时，结束循环
5. 超过 `max_chapters` 硬上限时，暂停工作流（`pause_reason: max_chapters_reached`）
```

---

## 6. 中断恢复与跳过

```yaml
chapter_generation:
  on_fail: "pause"           # pause / skip / fail
  skip_config:
    max_skips: 3
    mark_for_retry: true
```

> `retry` 不是 `on_fail` 的职责：
> - **LLM 调用层** 的瞬时错误重试由 `workflow.retry` 控制（见 [09-error-handling](./09-error-handling.md)）。
> - **节点执行级** 的重跑由安全阀 `workflow.safety.max_retry_per_node` / `max_total_retries` 控制（见 [08-cost-and-safety](./08-cost-and-safety.md)）。
> `on_fail` 只定义“重试/重跑耗尽后怎么办”。

| 策略 | 行为 |
|------|------|
| `pause` | 暂停工作流，等待用户处理（**默认**） |
| `skip` | 标记当前章节为 skipped，继续下一章 |
| `fail` | 立即终止整个工作流 |

### 6.1 循环内暂停策略（用于“混合体验”）

章节生成通常以一个循环节点（如 `chapter_gen`）实现：节点数量固定，但内部可迭代生成任意多章。

**需求**：既支持全手动逐章确认，也支持全自动批量生成，还支持“每 N 章暂停一次让用户检查”的混合体验。

**结论**：不新增 `workflow.mode: hybrid`。混合体验由循环节点的 `loop.pause` 表达。

**配置位置（示例）**：

```yaml
workflow:
  mode: "auto"  # manual / auto
  nodes:
    - id: "chapter_gen"
      loop:
        enabled: true
        pause:
          strategy: "every_n"  # none / every / every_n
          every_n: 10          # 每 10 章暂停一次
```

**默认行为**：
- 若 `loop.pause` 未配置：`manual` 模式默认 `every`；`auto` 模式默认 `none`
- `every`：每章生成完成后暂停，等待用户确认再继续
- `every_n`：每批 N 章暂停一次（批次内仍可自动审核/精修）

恢复时：检查**当前 `workflow_execution_id` 下**的 `chapter_tasks` → 找到第一个 `status` 不在 `("completed", "skipped")` 的章节（如 pending/interrupted/failed）→ 从该章节继续。

### 6.2 暂停后用户可执行的操作

工作流暂停后（无论是用户主动暂停、loop.pause 触发、还是错误导致），用户可以执行以下操作：

| 操作 | 说明 |
|------|------|
| 查看/编辑已生成章节 | 打开任意已完成章节进行编辑，保存新版本 |
| 修改 ChapterTask | 调整后续章节的任务描述（brief）、关键角色、关键事件 |
| 调整 Workflow 配置 | 切换审核 Agent、修改精修策略、调整预算等 |
| 跳过某些章节 | 将指定章节标记为 `skipped`，恢复后跳过这些章节 |
| 从某章重新开始 | 选择一个章节号，恢复后从该章重新生成（之后的章节重置为 pending） |
| 切换工作模式 | 从自动切换为手动，或反之 |
| 取消工作流 | 放弃本次执行，进入 `cancelled` 终态 |
| 恢复工作流 | 从暂停点继续执行 |

**约束：**
- 编辑已完成章节会触发下游 stale 标记（详见 [内容编辑](./05-content-editor.md) §7）
- 修改 ChapterTask 不影响已完成的章节，只影响后续待生成的章节
- 调整 Workflow 配置后恢复时，使用新配置继续执行（但启动时的配置快照不变）

---

## 7. 循环节点完成语义

```
循环节点"完成"定义：
  completed = 所有迭代达到终态（completed 或 skipped）
  failed    = 有任一迭代 failed 且未被 skip
  interrupted = 非终态，表示工作流暂停等待人工决策

示例：
  50 章全部 completed          → 循环完成 → export 启动
  48 completed + 2 skipped    → 循环完成 → export 启动
  48 completed + 2 failed     → 循环失败 → export 不启动

on_fail 策略影响：
  "pause" → 暂停等待用户
  "skip"  → 失败标记 skipped，循环继续
  "fail"  → 立即终止工作流
```

---

## 8. 与审核精修的交互

章节循环中，`on_fail` 和 `on_fix_fail` 作用于不同阶段，不冲突：

```
章节生成（Skill 调用）
  ├─ 成功 → 进入审核（03-review-and-fix）
  │         ├─ 审核通过 → 章节完成
  │         └─ 审核失败 → 触发精修
  │                       ├─ 精修成功 → 重新审核
  │                       └─ 精修失败（达 max_fix_attempts）→ 由 on_fix_fail 控制
  │                             pause / skip / fail（见 03-review-and-fix.md §7）
  │
  └─ 失败（Skill 执行错误/超时）→ 由 on_fail 控制
        pause / skip / fail（见本文档 §6）
```

| 策略 | 作用阶段 | 配置位置 |
|------|---------|---------|
| `on_fail` | 章节**生成**失败（Skill 执行错误） | 本文档 §6，workflow 章节循环配置 |
| `on_fix_fail` | 章节**精修**失败（达到最大精修次数） | 03-review-and-fix §7，节点级配置 |

---

*最后更新: 2026-03-17*
