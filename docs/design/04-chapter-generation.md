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

```python
class ChapterTask(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "chapter_tasks"
    project_id: Mapped[uuid.UUID]
    workflow_execution_id: Mapped[uuid.UUID]
    chapter_number: Mapped[int]
    title: Mapped[str]
    brief: Mapped[str]                    # 章节摘要/任务描述
    status: Mapped[str]                   # pending / generating / interrupted / completed / failed / skipped
    content_id: Mapped[uuid.UUID | None]  # 关联生成的内容
```

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

循环逻辑：

```python
async def execute_chapter_loop(workflow_execution, config):
    chapter_num = 1
    while chapter_num <= config.max_chapters:
        result = await generate_chapter(chapter_num)
        if marker in result.output:
            result.output = result.output.replace(marker, "").strip()
            await save_and_finish(result)
            break
        if await check_outline_covered(project_id, chapter_num):
            break
        chapter_num += 1
    if chapter_num > config.max_chapters:
        await pause_workflow("max_chapters_reached")
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

> `retry` 不是 `on_fail` 的职责——重试由安全阀 `max_retry` 控制（见 [08-cost-and-safety](./08-cost-and-safety.md)）。`on_fail` 仅定义"重试耗尽后怎么办"。

| 策略 | 行为 |
|------|------|
| `pause` | 暂停工作流，等待用户处理（**默认**） |
| `skip` | 标记当前章节为 skipped，继续下一章 |
| `fail` | 立即终止整个工作流 |

恢复时：检查**当前 `workflow_execution_id` 下**的 `chapter_tasks` → 找到第一个 `status` 不在 `("completed", "skipped")` 的章节（如 pending/interrupted/failed）→ 从该章节继续。

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
